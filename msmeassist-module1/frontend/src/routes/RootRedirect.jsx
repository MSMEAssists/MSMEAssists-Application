import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { PageLoader } from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import * as profileService from "../services/profileService";
import { WIZARD_STEPS } from "../utils/constants";

/**
 * Landing route for authenticated users ("resume later"): loads the real
 * profile and routes to wherever the user left off, instead of always
 * dumping them back at Step 1.
 */
export default function RootRedirect() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [target, setTarget] = useState(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      setChecking(false);
      return;
    }

    (async () => {
      try {
        const profile = await profileService.getMyProfileOrNull();
        if (!profile) {
          setTarget("/onboarding/business");
        } else if (profile.completeness.percentage === 100 || profile.status === "active") {
          setTarget("/profile/completed");
        } else {
          const firstIncomplete = WIZARD_STEPS.find((s) => !profile.completeness.sections?.[s.key]);
          setTarget(`/onboarding/${firstIncomplete ? firstIncomplete.key : "review"}`);
        }
      } catch {
        setTarget("/onboarding/business");
      } finally {
        setChecking(false);
      }
    })();
  }, [authLoading, isAuthenticated]);

  if (authLoading || checking) return <PageLoader label="Loading your profile…" />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Navigate to={target} replace />;
}
