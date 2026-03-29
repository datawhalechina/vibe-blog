export interface AgentTokenBreakdown {
  input: number
  output: number
  cache_read: number
  cache_write: number
  calls: number
}

export interface TokenUsageSummary {
  total_input_tokens: number
  total_output_tokens: number
  total_cache_read_tokens: number
  total_cache_write_tokens: number
  total_tokens: number
  total_calls: number
  agent_breakdown: Record<string, AgentTokenBreakdown>
}
