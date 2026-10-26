import apiClient from "./apiClient";

const _recCache = new Map();
const REC_CACHE_TTL_MS = 60 * 1000; // 60 seconds

export const recommendationService = {
  /**
   * Fetches Explainable AI Recommendations using Pairwise LLM + BTL + MLE.
   */
  async getRankedRecommendations(topK = 5, customQuery = null, forceRefresh = false) {
    const cacheKey = `${topK}_${customQuery || "default"}`;
    const now = Date.now();
    if (!forceRefresh && _recCache.has(cacheKey)) {
      const entry = _recCache.get(cacheKey);
      if (now - entry.timestamp < REC_CACHE_TTL_MS) {
        return entry.data;
      }
    }

    const response = await apiClient.post("/recommendations/rank", {
      top_k: topK,
      custom_query: customQuery,
    });
    _recCache.set(cacheKey, { timestamp: now, data: response.data });
    return response.data;
  },

  /**
   * Solves an arbitrary pairwise comparison win matrix using BTL MLE.
   */
  async solveBtl(items, winMatrix) {
    const response = await apiClient.post("/recommendations/btl-solve", {
      items,
      win_matrix: winMatrix,
    });
    return response.data;
  },

  clearCache() {
    _recCache.clear();
  },
};

export default recommendationService;
