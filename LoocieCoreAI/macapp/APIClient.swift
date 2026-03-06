import Foundation

final class APIClient {
    static let shared = APIClient()
    private init() {}

    func getHealth(baseURL: URL) async throws -> HealthResponse {
        let url = baseURL.appendingPathComponent("health")
        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        req.timeoutInterval = 5

        let (data, resp) = try await URLSession.shared.data(for: req)
        try Self.ensureOK(resp)
        return try JSONDecoder().decode(HealthResponse.self, from: data)
    }

    func getStatus(baseURL: URL, apiKey: String) async throws -> StatusResponse {
        let url = baseURL.appendingPathComponent("status")
        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        req.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        req.timeoutInterval = 5

        let (data, resp) = try await URLSession.shared.data(for: req)
        try Self.ensureOK(resp)
        return try JSONDecoder().decode(StatusResponse.self, from: data)
    }

    func postChat(baseURL: URL, apiKey: String, request: ChatRequest) async throws -> ChatResponse {
        let url = baseURL.appendingPathComponent("chat")
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        req.timeoutInterval = 10
        req.httpBody = try JSONEncoder().encode(request)

        let (data, resp) = try await URLSession.shared.data(for: req)
        try Self.ensureOK(resp)
        return try JSONDecoder().decode(ChatResponse.self, from: data)
    }

    private static func ensureOK(_ resp: URLResponse) throws {
        guard let http = resp as? HTTPURLResponse else { return }
        if http.statusCode >= 400 {
            throw NSError(domain: "LoocieCoreAI.API", code: http.statusCode, userInfo: [
                NSLocalizedDescriptionKey: "HTTP \(http.statusCode)"
            ])
        }
    }
}
