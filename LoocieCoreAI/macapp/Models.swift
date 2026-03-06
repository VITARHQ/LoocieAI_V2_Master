import Foundation

struct HealthResponse: Codable {
    let status: String
    let engine: String
    let version: String
    let env: String
    let uptime_seconds: Double
    let warnings: [String]?
}

struct StatusResponse: Codable {
    let engine: String
    let model: String
    let provider: String
    let endpoint: String
    let model_name: String
    let last_error: String?
}

struct ChatRequest: Codable {
    let message: String
    let mode: String          // "text" | "voice"
    let conversation_id: String?
}

struct ChatResponse: Codable {
    let reply: String
    let citations: [String: String]?
    let warnings: [String]?
}
