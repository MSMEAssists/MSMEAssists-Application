import { Link } from "react-router-dom";
import Button from "../components/ui/Button";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-bg px-6 text-center">
      <div className="mb-2 font-display text-6xl font-bold text-navy-900">404</div>
      <p className="mb-7 text-sm text-ink-500">This page doesn't exist.</p>
      <Link to="/">
        <Button variant="secondary">Go home</Button>
      </Link>
    </div>
  );
}
