import { Routes, Route } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import OnboardingRoute from "./OnboardingRoute";
import RootRedirect from "./RootRedirect";

import LoginPage from "../pages/auth/LoginPage";
import RegisterPage from "../pages/auth/RegisterPage";
import BusinessStep from "../pages/onboarding/BusinessStep";
import LocationStep from "../pages/onboarding/LocationStep";
import FinancialStep from "../pages/onboarding/FinancialStep";
import CharacteristicsStep from "../pages/onboarding/CharacteristicsStep";
import RegistrationsStep from "../pages/onboarding/RegistrationsStep";
import DocumentsStep from "../pages/onboarding/DocumentsStep";
import ReviewStep from "../pages/onboarding/ReviewStep";
import ProfileCompletedPage from "../pages/ProfileCompletedPage";
import SchemesPlaceholderPage from "../pages/SchemesPlaceholderPage";
import FinanceLoanDashboardPage from "../modules/finance-loan/pages/FinanceLoanDashboardPage";
import ExportDashboardPage from "../modules/export-agent/pages/ExportDashboardPage";
import DecisionIntelligenceDashboardPage from "../pages/DecisionIntelligenceDashboardPage";
import AdminRoute from "./AdminRoute";
import AdminSchemesDashboardPage from "../pages/admin/AdminSchemesDashboardPage";
import NotFoundPage from "../pages/NotFoundPage";

import HomePage from "../pages/HomePage";
import PersonalizedReportPage from "../pages/PersonalizedReportPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<ProfileCompletedPage />} />

        <Route path="/onboarding" element={<OnboardingRoute />}>
          <Route path="business" element={<BusinessStep />} />
          <Route path="location" element={<LocationStep />} />
          <Route path="financial" element={<FinancialStep />} />
          <Route path="characteristics" element={<CharacteristicsStep />} />
          <Route path="registrations" element={<RegistrationsStep />} />
          <Route path="documents" element={<DocumentsStep />} />
          <Route path="review" element={<ReviewStep />} />
        </Route>

        <Route path="/profile/completed" element={<ProfileCompletedPage />} />
        <Route path="/report" element={<PersonalizedReportPage />} />
        <Route path="/personalized-report" element={<PersonalizedReportPage />} />

        <Route path="/schemes" element={<SchemesPlaceholderPage />} />
        <Route path="/finance-loan" element={<FinanceLoanDashboardPage />} />
        <Route path="/export" element={<ExportDashboardPage />} />
        <Route path="/decision" element={<DecisionIntelligenceDashboardPage />} />
        <Route path="/decision-intelligence" element={<DecisionIntelligenceDashboardPage />} />
      </Route>

      {/* Admin Protected Routes - strictly restricted to system administrators */}
      <Route element={<AdminRoute />}>
        <Route path="/admin" element={<AdminSchemesDashboardPage />} />
        <Route path="/admin/schemes" element={<AdminSchemesDashboardPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
