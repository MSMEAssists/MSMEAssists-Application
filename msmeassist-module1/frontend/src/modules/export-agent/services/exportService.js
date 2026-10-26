import apiClient from "../../../services/apiClient";

const exportService = {
  getExportAdvisory: async (payload = {}) => {
    const response = await apiClient.post("/export/advisory", payload);
    return response.data;
  },
};

export default exportService;
