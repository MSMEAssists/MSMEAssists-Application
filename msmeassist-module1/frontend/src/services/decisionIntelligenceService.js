import apiClient from "./apiClient";

/**
 * Module 5: Decision Intelligence & Master Agent Orchestration Service.
 *
 * Coordinates calls to the orchestrator endpoint:
 *   - POST /decision-intelligence/orchestrate
 *   - GET  /decision-intelligence/objectives
 */
const decisionIntelligenceService = {
  /**
   * Run the master multi-agent orchestration pipeline.
   *
   * @param {Object} payload
   * @param {string} payload.objective - "comprehensive" | "loan_finance" | "scheme_subsidy" | "compliance_first" | "export_growth"
   * @param {string|null} [payload.target_state]
   * @param {number|null} [payload.target_loan_amount_inr]
   * @param {string|null} [payload.target_loan_purpose]
   * @param {number} [payload.top_k]
   * @returns {Promise<Object>}
   */
  async orchestrateDecision({
    objective = "comprehensive",
    target_state = null,
    target_loan_amount_inr = null,
    target_loan_purpose = null,
    top_k = 5,
  } = {}) {
    const response = await apiClient.post("/decision-intelligence/orchestrate", {
      objective,
      target_state,
      target_loan_amount_inr,
      target_loan_purpose,
      top_k,
    });
    return response.data;
  },

  /**
   * Fetch available decision objectives and descriptions.
   *
   * @returns {Promise<Array<{ id: string, label: string, description: string }>>}
   */
  async getObjectives() {
    const response = await apiClient.get("/decision-intelligence/objectives");
    return response.data;
  },
};

export default decisionIntelligenceService;
