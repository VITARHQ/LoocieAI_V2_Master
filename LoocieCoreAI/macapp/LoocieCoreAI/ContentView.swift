import SwiftUI

struct ContentView: View {
    @EnvironmentObject var engine: EngineManager
    @State private var message: String = ""
    @State private var conversationId: String = "core"
    @State private var chatLog: [String] = ["LoocieCoreAI: Core Companion ready."]

    private var statusText: String {
        if engine.engineOnline && engine.modelOnline {
            return "Ready"
        }
        if engine.lastError == "Health failed: The operation couldn’t be completed. Operation not permitted"
            || engine.lastError == "Health failed: The operation couldn't be completed. Operation not permitted" {
            return "Starting engine..."
        }
        if !engine.lastError.isEmpty {
            return engine.lastError
        }
        if engine.engineOnline && !engine.modelOnline {
            return "Engine online. Waiting for model."
        }
        return "Starting up..."
    }

    private var engineLabel: String {
        if engine.engineOnline { return "Online" }
        if statusText == "Starting engine..." || statusText == "Starting up..." { return "Starting" }
        return "Offline"
    }

    private var modelLabel: String {
        if engine.modelOnline { return "Online" }
        if engine.engineOnline && !engine.modelOnline { return "Loading" }
        if statusText == "Starting engine..." || statusText == "Starting up..." { return "Waiting" }
        return "Offline"
    }

    var body: some View {
        VStack(spacing: 10) {
            HStack(spacing: 14) {
                Circle()
                    .frame(width: 10, height: 10)
                    .foregroundStyle(engine.engineOnline ? .green : .orange)
                Text("Engine: \(engineLabel)")

                Circle()
                    .frame(width: 10, height: 10)
                    .foregroundStyle(engine.modelOnline ? .green : .orange)
                Text("Model: \(modelLabel)")

                Spacer()

                Text(statusText)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)

                SettingsLink {
                    Text("Settings")
                }
            }
            .padding(.horizontal)
            .padding(.top, 8)

            Divider()

            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(Array(chatLog.enumerated()), id: \.offset) { index, line in
                            Text(line)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .textSelection(.enabled)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(.quaternary.opacity(0.35), in: RoundedRectangle(cornerRadius: 10))
                                .id(index)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.top, 8)
                    .padding(.bottom, 4)
                }
                .onChange(of: chatLog.count) { _, _ in
                    if let last = chatLog.indices.last {
                        withAnimation {
                            proxy.scrollTo(last, anchor: .bottom)
                        }
                    }
                }
            }

            Divider()

            HStack {
                TextField("Type message…", text: $message)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit { send() }

                Button("Send") { send() }
                    .disabled(message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            .padding(.horizontal)
            .padding(.bottom, 10)
        }
        .frame(minWidth: 760, minHeight: 520)
    }

    private func send() {
        let trimmed = message.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        message = ""
        chatLog.append("You: \(trimmed)")

        guard let baseURL = engine.baseURL else {
            chatLog.append("LoocieCoreAI: Invalid Base URL in Settings.")
            return
        }

        guard !engine.apiKey.isEmpty else {
            chatLog.append("LoocieCoreAI: API key missing in Settings.")
            return
        }

        Task {
            do {
                let req = ChatRequest(message: trimmed, mode: "text", conversation_id: conversationId)
                let resp = try await APIClient.shared.postChat(baseURL: baseURL, apiKey: engine.apiKey, request: req)
                await MainActor.run {
                    chatLog.append("LoocieCoreAI: \(resp.reply)")
                    if let warns = resp.warnings, !warns.isEmpty {
                        chatLog.append("Warnings: \(warns.joined(separator: " | "))")
                    }
                }
            } catch {
                await MainActor.run {
                    chatLog.append("LoocieCoreAI: Chat failed: \(error.localizedDescription)")
                }
            }
        }
    }
}
