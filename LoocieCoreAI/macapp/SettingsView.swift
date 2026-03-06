import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var engine: EngineManager

    var body: some View {
        Form {
            Section("Engine Connection") {
                TextField("Base URL", text: $engine.baseURLString)
                SecureField("X-API-Key", text: $engine.apiKey)

                Button("Refresh Status") {
                    Task { await engine.refreshStatus() }
                }
            }
        }
        .padding(16)
        .frame(width: 520)
    }
}
