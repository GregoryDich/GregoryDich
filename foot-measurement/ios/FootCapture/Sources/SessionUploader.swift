import Foundation
import Combine

/// SEND: zip the session directory (NSFileCoordinator .forUploading) and POST it as the
/// request body to `<serverURL>/sessions`; shows the JSON answer (length_mm / width_mm).
final class SessionUploader: ObservableObject {
    @Published var isUploading = false
    @Published var status = ""

    func send(sessionDir: URL, to serverURL: String) {
        guard let base = URL(string: serverURL.trimmingCharacters(in: .whitespacesAndNewlines)) else {
            status = "bad server URL"
            return
        }
        isUploading = true
        status = "zipping…"
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let zip = try Self.zipDirectory(sessionDir)
                let size = (try? FileManager.default.attributesOfItem(atPath: zip.path)[.size] as? Int) ?? 0
                DispatchQueue.main.async { self.status = "uploading \(size / 1_000_000) MB… (processing takes a while)" }

                var req = URLRequest(url: base.appendingPathComponent("sessions"))
                req.httpMethod = "POST"
                req.setValue("application/zip", forHTTPHeaderField: "Content-Type")
                req.timeoutInterval = 900
                let task = URLSession.shared.uploadTask(with: req, fromFile: zip) { data, resp, err in
                    DispatchQueue.main.async {
                        self.isUploading = false
                        if let err {
                            self.status = "error: \(err.localizedDescription)"
                            return
                        }
                        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
                        let body = data.flatMap { String(data: $0, encoding: .utf8) } ?? ""
                        if code == 200, let d = data,
                           let json = try? JSONSerialization.jsonObject(with: d) as? [String: Any],
                           let L = json["length_mm"] as? Double, let W = json["width_mm"] as? Double {
                            let frames = json["valid_frames"] ?? "-"
                            self.status = String(format: "Length: %.1f mm\nWidth:  %.1f mm\nvalid frames: %@", L, W, "\(frames)")
                        } else {
                            self.status = "HTTP \(code): \(body.prefix(400))"
                        }
                    }
                }
                task.resume()
            } catch {
                DispatchQueue.main.async {
                    self.isUploading = false
                    self.status = "zip failed: \(error.localizedDescription)"
                }
            }
        }
    }

    /// Zips a directory without third-party code: the `.forUploading` reading option hands
    /// the accessor a temporary zip archive that is only valid inside the block, so copy it out.
    static func zipDirectory(_ dir: URL) throws -> URL {
        let dest = FileManager.default.temporaryDirectory.appendingPathComponent(dir.lastPathComponent + ".zip")
        try? FileManager.default.removeItem(at: dest)
        var coordinatorError: NSError?
        var copyError: Error?
        NSFileCoordinator().coordinate(readingItemAt: dir, options: .forUploading, error: &coordinatorError) { tmp in
            do { try FileManager.default.copyItem(at: tmp, to: dest) } catch { copyError = error }
        }
        if let e = coordinatorError { throw e }
        if let e = copyError { throw e }
        return dest
    }
}
