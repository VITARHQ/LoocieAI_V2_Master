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
    private var engineProcess: Process?
    private var appStartedEngine: Bool = false

    private let launcherPath = "/Volumes/LoocieCoreAI/LoocieCoreAI_Core/LoocieAI_V2_Master/LoocieCoreAI/macapp/scripts/START_ENGINE_FOREGROUND.sh"

    private init() {
        Task {
            await ensureEngineRunning()
            startPolling()
        }
    }

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
        Task {
            stopOwnedEngine()
            try? await Task.sleep(nanoseconds: 500_000_000)
            await ensureEngineRunning()
        }
    }

    func stopOwnedEngine() {
        guard appStartedEngine, let process = engineProcess else { return }

        if process.isRunning {
            process.terminate()
        }

        engineProcess = nil
        appStartedEngine = false

        Task { @MainActor in
            self.engineOnline = false
            self.modelOnline = false
            self.lastError = "Engine stopped."
        }
    }

    private func ensureEngineRunning() async {
        if await isHealthOK() {
            await MainActor.run {
                self.lastError = ""
            }
            return
        }

        guard FileManager.default.isExecutableFile(atPath: launcherPath) else {
            await MainActor.run {
                self.lastError = "Launcher not executable: \(self.launcherPath)"
            }
            return
        }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: launcherPath)

        let outPipe = Pipe()
        let errPipe = Pipe()
        process.standardOutput = outPipe
        process.standardError = errPipe

        do {
            try process.run()
            engineProcess = process
            appStartedEngine = true
        } catch {
            await MainActor.run {
                self.lastError = "Failed to start engine: \(error.localizedDescription)"
            }
            return
        }

        let ready = await waitForHealthReady(timeoutSeconds: 15)
        await MainActor.run {
            self.engineOnline = ready
            if !ready {
                self.lastError = "Engine failed to become ready in time."
            }
        }
    }

    private func isHealthOK() async -> Bool {
        guard let baseURL = baseURL else { return false }
        do {
            _ = try await APIClient.shared.getHealth(baseURL: baseURL)
            return true
        } catch {
            return false
        }
    }

    private func waitForHealthReady(timeoutSeconds: Int) async -> Bool {
        let deadline = Date().addingTimeInterval(TimeInterval(timeoutSeconds))
        while Date() < deadline {
            if await isHealthOK() {
                return true
            }
            try? await Task.sleep(nanoseconds: 500_000_000)
        }
        return false
    }
}
