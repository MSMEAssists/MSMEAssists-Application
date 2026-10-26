import apiClient from "./apiClient";

/**
 * Scheme Compliance Agent — frontend API service.
 *
 * Mirrors schemesService.js exactly:
 *   - uses the shared apiClient (Bearer token injected automatically)
 *   - base path is relative to VITE_API_BASE_URL ("/api" by default)
 */
const _COMPLIANCE_CLIENT_CACHE = new Map();
const _IN_FLIGHT_REQUESTS = new Map();
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Scheme Compliance Agent — frontend API service with in-memory caching
 * and request deduplication.
 */
const complianceService = {
  /**
   * Run a scheme-specific compliance assessment for the authenticated user.
   *
   * @param {{
   *   schemeId: string,
   *   schemeName: string,
   *   schemeOrganization?: string,
   *   officialUrl?: string,
   *   knowledgeType?: string,
   *   documentId?: string,
   *   sourceId?: string,
   *   forceRefresh?: boolean,
   * }} params
   * @returns {Promise<any>}
   */
  async checkSchemeCompliance({
    schemeId,
    schemeName,
    schemeOrganization,
    officialUrl,
    knowledgeType,
    documentId,
    sourceId,
    forceRefresh = false,
  }) {
    const cacheKey = `comp_${schemeId || ""}_${schemeName || ""}`.toLowerCase().trim();

    if (!forceRefresh) {
      const cached = _COMPLIANCE_CLIENT_CACHE.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
        return cached.data;
      }
      if (_IN_FLIGHT_REQUESTS.has(cacheKey)) {
        return await _IN_FLIGHT_REQUESTS.get(cacheKey);
      }
    }

    const requestPromise = (async () => {
      try {
        const response = await apiClient.post("/compliance/scheme-check", {
          scheme_id:           schemeId,
          scheme_name:         schemeName,
          scheme_organization: schemeOrganization ?? null,
          official_url:        officialUrl        ?? null,
          knowledge_type:      knowledgeType      ?? "SCHEME",
          document_id:         documentId         ?? null,
          source_id:           sourceId           ?? null,
        });

        if (response.data) {
          _COMPLIANCE_CLIENT_CACHE.set(cacheKey, {
            timestamp: Date.now(),
            data: response.data,
          });
        }
        return response.data;
      } finally {
        _IN_FLIGHT_REQUESTS.delete(cacheKey);
      }
    })();

    _IN_FLIGHT_REQUESTS.set(cacheKey, requestPromise);
    return await requestPromise;
  },

  clearCache() {
    _COMPLIANCE_CLIENT_CACHE.clear();
    _IN_FLIGHT_REQUESTS.clear();
  },
};

export default complianceService;
