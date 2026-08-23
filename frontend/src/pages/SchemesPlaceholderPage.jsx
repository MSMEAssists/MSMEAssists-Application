import { useNavigate } from "react-router-dom";
import { FiClock } from "react-icons/fi";
import AppLayout from "../layouts/AppLayout";
import Button from "../components/ui/Button";

export default function SchemesPlaceholderPage() {
  const navigate = useNavigate();
  return (
    <AppLayout>
      <div className="mx-auto flex max-w-lg flex-col items-center px-6 py-24 text-center">
        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-teal-100">
          <FiClock size={28} className="text-teal-600" />
        </div>
        <h2 className="mb-2 text-xl">Government Scheme Discovery</h2>
        <p className="mb-8 text-sm leading-relaxed text-ink-500">
          This is where MSMEAssist will match your business profile to relevant government schemes — that
          capability is being built as a separate module and isn't available yet.
        </p>
        <Button variant="secondary" onClick={() => navigate("/profile/completed")}>
          ← Back to your profile
        </Button>
      </div>
    </AppLayout>
  );
}
