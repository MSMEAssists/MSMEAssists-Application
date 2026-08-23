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
import NotFoundPage from "../pages/NotFoundPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<RootRedirect />} />

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

        {/* Placeholder only — Module 2 itself is out of scope for this build. */}
        <Route path="/schemes" element={<SchemesPlaceholderPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
