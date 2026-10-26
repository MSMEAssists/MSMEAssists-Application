import apiClient from "./apiClient";

export const adminService = {
  /**
   * Fetches all schemes with location, dual URLs, and link status for admin management.
   */
  async getSchemes({ locationFilter = null, search = null } = {}) {
    const params = {};
    if (locationFilter && locationFilter !== "all") {
      params.location_filter = locationFilter;
    }
    if (search && search.trim()) {
      params.search = search.trim();
    }
    const response = await apiClient.get("/admin/schemes", { params });
    return response.data;
  },

  /**
   * Tests link health for a single scheme live via HTTP.
   */
  async checkSchemeLink(documentId) {
    const response = await apiClient.post(`/admin/schemes/${documentId}/check-link`);
    return response.data;
  },

  /**
   * Batch tests unique portal URLs live.
   */
  async checkAllLinks() {
    const response = await apiClient.post("/admin/schemes/check-all-links");
    return response.data;
  },

  /**
   * Permanently deletes a scheme from the database and vector store.
   */
  async deleteScheme(documentId) {
    const response = await apiClient.delete(`/admin/schemes/${documentId}`);
    return response.data;
  },

  /**
   * Development / demo helper: toggle current user's role between admin and msme_owner.
   */
  async toggleAdminRole() {
    const response = await apiClient.post("/admin/toggle-admin-role");
    return response.data;
  },
};

export default adminService;
