import apiClient from "../../../services/apiClient";

export const financeLoanService = {
  /**
   * Post request for financial position & cash flow analysis
   */
  analyzeFinancials: async (financialInputs = {}, businessProfile = {}) => {
    const response = await apiClient.post("/finance/analyze", {
      financial_inputs: financialInputs,
      business_profile: businessProfile,
    });
    return response.data;
  },

  /**
   * Post request for complete Finance & Loan Advisory recommendation
   */
  getLoanRecommendations: async (
    financialInputs = {},
    loanInputs = {},
    businessProfile = {},
    useModule3Rankings = true
  ) => {
    const response = await apiClient.post("/finance/loan-recommendation", {
      financial_inputs: financialInputs,
      loan_inputs: loanInputs,
      business_profile: businessProfile,
      use_module3_rankings: useModule3Rankings,
      top_k: 5,
    });
    return response.data;
  },

  /**
   * Get supported financing categories
   */
  getFinancingCategories: async () => {
    const response = await apiClient.get("/finance/options");
    return response.data;
  },
};

export default financeLoanService;
