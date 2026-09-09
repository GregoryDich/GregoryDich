import ARKit
import AVFoundation
import Combine
import UIKit

/// Records a measurement session:
///
///     Documents/sessions/<yyyyMMdd-HHmmss>/
///         video.mov        H.264, frame i  <->  frames[i] in metadata.json
///         depth.bin        float32 LE depth maps (metres) back to back, 192 rows x 256 cols each
///         confidence.bin   uint8 confidence maps (0 low / 1 medium / 2 high) back to back
///         metadata.json    per-frame intrinsics / camera transform / timestamps
///
/// Video and depth are kept in lock-step: a depth frame is written only after the
/// matching video frame was accepted by the AVAssetWriter.  The captured image is
/// copied into a pool buffer so no ARFrame is retained by the encoder.
final class SessionRecorder: NSObject, ObservableObject, ARSessionDelegate {
    let session = ARSession()

    @Published var isReady = false
    @Published var isRecording = false
    @Published var status = "starting…"
    @Published var frameCount = 0
    @Published var lastSessionURL: URL?

    static let maxDuration: TimeInterval = 10   // auto-STOP (thermal / size)

    private let delegateQueue = DispatchQueue(label: "footcapture.arsession")
    private let ioQueue = DispatchQueue(label: "footcapture.io")

    // recording state — touched only on delegateQueue
    private var recording = false
    private var writer: AVAssetWriter?
    private var writerInput: AVAssetWriterInput?
    private var adaptor: AVAssetWriterInputPixelBufferAdaptor?
    private var depthHandle: FileHandle?
    private var confHandle: FileHandle?
    private var frames: [[String: Any]] = []
    private var startTimestamp: TimeInterval?
    private var sessionDir: URL?
    private var depthSize = (width: 0, height: 0)
    private var interfaceOrientation = "portrait"
    private var autoStop: DispatchWorkItem?

    private var videoSize = CGSize(width: 1920, height: 1440)
    private var videoFPS = 30

    // MARK: - AR session

    func startSession() {
        guard ARWorldTrackingConfiguration.isSupported,
              ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth) else {
            status = "sceneDepth not supported on this device (LiDAR required)"
            return
        }
        let config = ARWorldTrackingConfiguration()
        config.frameSemantics = [.sceneDepth]
        // Prefer the 4:3 1920x1440 @ 30 fps format (the depth map is 256x192, same aspect).
        if let fmt = ARWorldTrackingConfiguration.supportedVideoFormats.first(where: {
            $0.imageResolution == CGSize(width: 1920, height: 1440) && $0.framesPerSecond == 30
        }) {
            config.videoFormat = fmt
        }
        videoSize = config.videoFormat.imageResolution
        videoFPS = config.videoFormat.framesPerSecond
        config.isAutoFocusEnabled = true
        session.delegate = self
        session.delegateQueue = delegateQueue
        session.run(config)
        isReady = true
        status = "ready: \(Int(videoSize.width))x\(Int(videoSize.height)) @ \(videoFPS) fps + sceneDepth"
    }

    // MARK: - START

    func startRecording() {
        guard !isRecording else { return }
        do {
            let dir = try Self.makeSessionDirectory()
            let (w, input, adaptor) = try makeWriter(in: dir)
            let depthURL = dir.appendingPathComponent("depth.bin")
            let confURL = dir.appendingPathComponent("confidence.bin")
            FileManager.default.createFile(atPath: depthURL.path, contents: nil)
            FileManager.default.createFile(atPath: confURL.path, contents: nil)
            let dh = try FileHandle(forWritingTo: depthURL)
            let ch = try FileHandle(forWritingTo: confURL)
            let orientation = Self.currentInterfaceOrientation()

            delegateQueue.async {
                self.writer = w
                self.writerInput = input
                self.adaptor = adaptor
                self.depthHandle = dh
                self.confHandle = ch
                self.frames = []
                self.startTimestamp = nil
                self.sessionDir = dir
                self.interfaceOrientation = orientation
                self.recording = true
            }
            isRecording = true
            lastSessionURL = nil
            frameCount = 0
            status = "recording → \(dir.lastPathComponent)"

            let work = DispatchWorkItem { [weak self] in self?.stopRecording() }
            autoStop = work
            DispatchQueue.main.asyncAfter(deadline: .now() + Self.maxDuration, execute: work)
        } catch {
            status = "START failed: \(error.localizedDescription)"
        }
    }

    private func makeWriter(in dir: URL) throws -> (AVAssetWriter, AVAssetWriterInput, AVAssetWriterInputPixelBufferAdaptor) {
        let w = try AVAssetWriter(outputURL: dir.appendingPathComponent("video.mov"), fileType: .mov)
        let settings: [String: Any] = [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: Int(videoSize.width),
            AVVideoHeightKey: Int(videoSize.height),
            AVVideoCompressionPropertiesKey: [
                AVVideoAverageBitRateKey: 20_000_000,
                AVVideoExpectedSourceFrameRateKey: videoFPS,
                AVVideoMaxKeyFrameIntervalKey: videoFPS,
            ],
        ]
        let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
        input.expectsMediaDataInRealTime = true
        // NOTE: no input.transform — frames stay in the sensor (landscape) orientation, like the intrinsics.
        let attrs: [String: Any] = [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarFullRange,
            kCVPixelBufferWidthKey as String: Int(videoSize.width),
            kCVPixelBufferHeightKey as String: Int(videoSize.height),
        ]
        let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: attrs)
        guard w.canAdd(input) else { throw RecorderError("cannot add video input") }
        w.add(input)
        guard w.startWriting() else { throw w.error ?? RecorderError("startWriting failed") }
        w.startSession(atSourceTime: .zero)   // pixelBufferPool becomes available after startWriting()
        return (w, input, adaptor)
    }

    // MARK: - frames

    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        guard recording, let adaptor, let input = writerInput, let sceneDepth = frame.sceneDepth else { return }
        guard input.isReadyForMoreMediaData, let pool = adaptor.pixelBufferPool else { return }   // drop frame

        if startTimestamp == nil { startTimestamp = frame.timestamp }
        let t = frame.timestamp - startTimestamp!

        // 1) copy the captured image into a pool buffer and hand it to the encoder
        var copy: CVPixelBuffer?
        CVPixelBufferPoolCreatePixelBuffer(nil, pool, &copy)
        guard let dst = copy, Self.copyPlanes(from: frame.capturedImage, to: dst) else { return }
        let pts = CMTime(seconds: t, preferredTimescale: 1_000_000)
        guard adaptor.append(dst, withPresentationTime: pts) else { return }   // not accepted -> no depth either

        // 2) depth + confidence (copied now; written on the io queue)
        let depthMap = sceneDepth.depthMap
        if depthSize.width == 0 {
            depthSize = (CVPixelBufferGetWidth(depthMap), CVPixelBufferGetHeight(depthMap))
        }
        let depthData = Self.copyRows(depthMap, bytesPerPixel: 4)
        let confData: Data
        if let cm = sceneDepth.confidenceMap {
            confData = Self.copyRows(cm, bytesPerPixel: 1)
        } else {
            confData = Data(repeating: 2, count: depthSize.width * depthSize.height)
        }

        // 3) calibration
        let K = frame.camera.intrinsics          // simd_float3x3, column-major: K[col][row]
        let T = frame.camera.transform           // camera -> world, simd_float4x4
        var rowMajor: [Double] = []
        rowMajor.reserveCapacity(16)
        for r in 0..<4 { for c in 0..<4 { rowMajor.append(Double(T[c][r])) } }

        let record: [String: Any] = [
            "index": frames.count,
            "t": t,
            "timestamp": frame.timestamp,
            "fx": Double(K[0][0]), "fy": Double(K[1][1]),
            "cx": Double(K[2][0]), "cy": Double(K[2][1]),
            "transform_row_major": rowMajor,
            "exposure_duration": frame.camera.exposureDuration,
        ]
        frames.append(record)
        let n = frames.count
        ioQueue.async { [depthHandle, confHandle] in
            depthHandle?.write(depthData)
            confHandle?.write(confData)
        }
        if n % 5 == 0 {
            DispatchQueue.main.async { self.frameCount = n }
        }
    }

    func session(_ session: ARSession, didFailWithError error: Error) {
        DispatchQueue.main.async { self.status = "AR error: \(error.localizedDescription)" }
    }

    // MARK: - STOP

    func stopRecording() {
        autoStop?.cancel()
        guard isRecording else { return }
        isRecording = false
        status = "finishing…"
        delegateQueue.async {
            self.recording = false
            let frames = self.frames
            let writer = self.writer
            let input = self.writerInput
            let dir = self.sessionDir
            let depthSize = self.depthSize
            let orientation = self.interfaceOrientation
            let dh = self.depthHandle, ch = self.confHandle
            self.writer = nil; self.writerInput = nil; self.adaptor = nil
            self.depthHandle = nil; self.confHandle = nil
            input?.markAsFinished()
            self.ioQueue.async {
                try? dh?.close()
                try? ch?.close()
                guard let writer, let dir else { return }
                writer.finishWriting {
                    let meta: [String: Any] = [
                        "device": Self.machineIdentifier(),
                        "ios": UIDevice.current.systemVersion,
                        "interface_orientation": orientation,
                        "video": ["path": "video.mov", "width": Int(self.videoSize.width),
                                  "height": Int(self.videoSize.height), "fps": self.videoFPS, "codec": "h264"],
                        "depth": ["width": depthSize.width, "height": depthSize.height,
                                  "dtype": "float32", "unit": "m", "confidence_dtype": "uint8"],
                        "frames": frames,
                    ]
                    var msg: String
                    do {
                        let data = try JSONSerialization.data(withJSONObject: meta, options: [.prettyPrinted, .sortedKeys])
                        try data.write(to: dir.appendingPathComponent("metadata.json"))
                        msg = "saved \(frames.count) frames → \(dir.lastPathComponent)"
                        if let e = writer.error { msg += " (writer error: \(e.localizedDescription))" }
                    } catch {
                        msg = "metadata write failed: \(error.localizedDescription)"
                    }
                    DispatchQueue.main.async {
                        self.frameCount = frames.count
                        self.lastSessionURL = dir
                        self.status = msg
                    }
                }
            }
        }
    }

    // MARK: - helpers

    private static func makeSessionDirectory() throws -> URL {
        let f = DateFormatter()
        f.dateFormat = "yyyyMMdd-HHmmss"
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let dir = docs.appendingPathComponent("sessions").appendingPathComponent(f.string(from: Date()))
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    /// The app is portrait-only, so this is normally "portrait"; kept explicit for the Python side
    /// (the sensor image itself is always landscape-right).
    private static func currentInterfaceOrientation() -> String {
        let scene = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first
        switch scene?.interfaceOrientation {
        case .portrait: return "portrait"
        case .portraitUpsideDown: return "portraitUpsideDown"
        case .landscapeLeft: return "landscapeLeft"
        case .landscapeRight: return "landscapeRight"
        default: return "portrait"
        }
    }

    private static func machineIdentifier() -> String {
        var sys = utsname()
        uname(&sys)
        return withUnsafePointer(to: &sys.machine) {
            $0.withMemoryRebound(to: CChar.self, capacity: 1) { String(cString: $0) }
        }
    }

    /// Copy all planes of a (bi-planar YCbCr) pixel buffer, honouring bytesPerRow padding.
    private static func copyPlanes(from src: CVPixelBuffer, to dst: CVPixelBuffer) -> Bool {
        CVPixelBufferLockBaseAddress(src, .readOnly)
        CVPixelBufferLockBaseAddress(dst, [])
        defer {
            CVPixelBufferUnlockBaseAddress(src, .readOnly)
            CVPixelBufferUnlockBaseAddress(dst, [])
        }
        let planes = max(1, CVPixelBufferGetPlaneCount(src))
        guard CVPixelBufferGetPlaneCount(dst) == CVPixelBufferGetPlaneCount(src),
              CVPixelBufferGetWidth(src) == CVPixelBufferGetWidth(dst),
              CVPixelBufferGetHeight(src) == CVPixelBufferGetHeight(dst) else { return false }
        for p in 0..<planes {
            guard let s = CVPixelBufferGetBaseAddressOfPlane(src, p),
                  let d = CVPixelBufferGetBaseAddressOfPlane(dst, p) else { return false }
            let sbpr = CVPixelBufferGetBytesPerRowOfPlane(src, p)
            let dbpr = CVPixelBufferGetBytesPerRowOfPlane(dst, p)
            let rows = CVPixelBufferGetHeightOfPlane(src, p)
            let n = min(sbpr, dbpr)
            if sbpr == dbpr {
                memcpy(d, s, sbpr * rows)
            } else {
                for r in 0..<rows { memcpy(d + r * dbpr, s + r * sbpr, n) }
            }
        }
        return true
    }

    /// Tightly packed row-major copy of a single-plane buffer (depth float32 / confidence uint8).
    private static func copyRows(_ buf: CVPixelBuffer, bytesPerPixel: Int) -> Data {
        CVPixelBufferLockBaseAddress(buf, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(buf, .readOnly) }
        let w = CVPixelBufferGetWidth(buf), h = CVPixelBufferGetHeight(buf)
        let bpr = CVPixelBufferGetBytesPerRow(buf)
        let rowBytes = w * bytesPerPixel
        var data = Data(count: rowBytes * h)
        guard let base = CVPixelBufferGetBaseAddress(buf) else { return data }
        data.withUnsafeMutableBytes { (out: UnsafeMutableRawBufferPointer) in
            guard let o = out.baseAddress else { return }
            if bpr == rowBytes {
                memcpy(o, base, rowBytes * h)
            } else {
                for r in 0..<h { memcpy(o + r * rowBytes, base + r * bpr, rowBytes) }
            }
        }
        return data
    }
}

struct RecorderError: LocalizedError {
    let message: String
    init(_ m: String) { message = m }
    var errorDescription: String? { message }
}
