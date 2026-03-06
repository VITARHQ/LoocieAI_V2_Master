import Foundation
import SwiftUI
import Combine

final class EngineManager: ObservableObject {
    static let shared = EngineManager()

    @Published var engineOnline: Bool = false
    @Published var modelOnline: Bool = false
    @Published var lastError: String = ""
    @Published var baseURLString: String = "http://127.0.0.1:8080"
    @Published var apiKey: String = ""

    private var pollTask: Task<Void, Never>?

    private init() { startPolling() }

    var baseURL: URL? { URL(string: baseURLString) }

    func startPolling() {
        pollTask?.cancel()
        pollTask = Task { [weak self] in
            while let self = self, !Task.isCancelled {
                await self.refreshStatus()
                try? await Task.sleep(nanoseconds: 1_000_000_000)
            }
        }
    }

    @MainActor
    func refreshStatus() async {
        print("LoocieCoreAI baseURLString=", baseURLString)
        guard let baseURL = baseURL else {
            engineOnline = false
            modelOnline = false
            lastError = "Invalid base URL"
            return
        }

        do {
            _ = try await APIClient.shared.getHealth(baseURL: baseURL)
            engineOnline = true
        } catch {
            engineOnline = false
            modelOnline = false
            lastError = "Health failed: \(error.localizedDescription)"
            return
        }

        guard !apiKey.isEmpty else {
            modelOnline = false
            lastError = "Set X-API-Key in Settings."
            return
        }

        do {
            let st = try await APIClient.shared.getStatus(baseURL: baseURL, apiKey: apiKey)
            modelOnline = (st.model == "online")
            lastError = st.last_error ?? ""
        } catch {
            modelOnline = false
            lastError = "Status failed: \(error.localizedDescription)"
        }
    }

    func restartEngineUserInitiated() {
        // Build/Test placeholder for now
    }
}
