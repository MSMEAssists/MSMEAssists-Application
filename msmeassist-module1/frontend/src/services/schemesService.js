import apiClient from "./apiClient";

let _cachedDiscoveredSchemes = null;
let _cachedDiscoveredTime = 0;
const CACHE_TTL_MS = 60 * 1000; // 60 seconds

const _chatCache = new Map();

export const schemesService = {
  /**
   * Fetches government schemes tailored to the user's business profile.
   * Eligibility, ranking, and evidence fields are produced by the backend.
   */
  async getDiscoveredSchemes(forceRefresh = false) {
    const now = Date.now();
    if (!forceRefresh && _cachedDiscoveredSchemes && (now - _cachedDiscoveredTime < CACHE_TTL_MS)) {
      return _cachedDiscoveredSchemes;
    }
    const response = await apiClient.get("/schemes/discovery");
    _cachedDiscoveredSchemes = response.data;
    _cachedDiscoveredTime = now;
    return response.data;
  },

  /**
   * Submits a question to the official Government Information RAG System and Personalized Advisor.
   * @param {{ query: string, topK?: number, knowledgeType?: string, conversationHistory?: Array<{role: string, content: string}>, currentSchemeId?: string }} params
   */
  async queryAssistant({ query, topK = 5, knowledgeType = null, conversationHistory = null, currentSchemeId = null, signal = null }) {
    const isInteractive = Boolean(conversationHistory?.length || currentSchemeId);
    const cacheKey = `${(query || "").trim().toLowerCase()}_${topK}_${knowledgeType || "all"}`;
    const now = Date.now();
    if (!isInteractive && _chatCache.has(cacheKey)) {
      const entry = _chatCache.get(cacheKey);
      if (now - entry.timestamp < CACHE_TTL_MS * 3) {
        return entry.data;
      }
    }

    const payload = { query };
    if (topK) payload.top_k = topK;
    if (knowledgeType) payload.knowledge_type = knowledgeType;
    if (conversationHistory) payload.conversation_history = conversationHistory;
    if (currentSchemeId) payload.current_scheme_id = currentSchemeId;

    const response = await apiClient.post("/schemes/query", payload, { signal });
    if (!isInteractive) {
      _chatCache.set(cacheKey, { timestamp: now, data: response.data });
    }
    return response.data;
  },

  clearCache() {
    _cachedDiscoveredSchemes = null;
    _cachedDiscoveredTime = 0;
    _chatCache.clear();
  },
};

export default schemesService;
