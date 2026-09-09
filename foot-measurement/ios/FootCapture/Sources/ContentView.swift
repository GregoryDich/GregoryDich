import SwiftUI
import ARKit
import RealityKit

/// Camera preview driven by the recorder's ARSession (we configure the session ourselves).
struct ARPreview: UIViewRepresentable {
    let session: ARSession

    func makeUIView(context: Context) -> ARView {
        let view = ARView(frame: .zero, cameraMode: .ar, automaticallyConfigureSession: false)
        view.session = session
        view.renderOptions = [.disableMotionBlur, .disableDepthOfField, .disableHDR]
        return view
    }

    func updateUIView(_ uiView: ARView, context: Context) {}
}

/// MVP UI: START / STOP / SEND (+ server URL field and a status line). No design.
struct ContentView: View {
    @StateObject private var recorder = SessionRecorder()
    @StateObject private var uploader = SessionUploader()
    @AppStorage("serverURL") private var serverURL = "http://192.168.1.10:8000"

    var body: some View {
        ZStack(alignment: .bottom) {
            ARPreview(session: recorder.session)
                .ignoresSafeArea()

            VStack(spacing: 10) {
                Text(recorder.status)
                    .font(.footnote.monospaced())
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity, alignment: .leading)

                if recorder.isRecording {
                    Text("REC  \(recorder.frameCount) frames")
                        .font(.headline)
                        .foregroundColor(.red)
                }

                TextField("http://<mac-ip>:8000", text: $serverURL)
                    .textFieldStyle(.roundedBorder)
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()

                HStack(spacing: 12) {
                    Button("START") { recorder.startRecording() }
                        .disabled(recorder.isRecording || !recorder.isReady)
                    Button("STOP") { recorder.stopRecording() }
                        .disabled(!recorder.isRecording)
                    Button("SEND") {
                        if let dir = recorder.lastSessionURL {
                            uploader.send(sessionDir: dir, to: serverURL)
                        }
                    }
                    .disabled(recorder.lastSessionURL == nil || recorder.isRecording || uploader.isUploading)
                }
                .buttonStyle(.borderedProminent)
                .font(.title3.bold())

                if !uploader.status.isEmpty {
                    Text(uploader.status)
                        .font(.body.monospaced())
                        .foregroundColor(.yellow)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .padding()
            .background(Color.black.opacity(0.55))
        }
        .onAppear { recorder.startSession() }
    }
}
