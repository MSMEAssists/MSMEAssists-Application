import { Outlet } from "react-router-dom";
import { OnboardingProvider } from "../context/OnboardingContext";
import OnboardingLayout from "../layouts/OnboardingLayout";

export default function OnboardingRoute() {
  return (
    <OnboardingProvider>
      <OnboardingLayout>
        <Outlet />
      </OnboardingLayout>
    </OnboardingProvider>
  );
}
