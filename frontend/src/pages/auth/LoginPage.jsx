import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import AuthLayout from "../../layouts/AuthLayout";
import Input from "../../components/ui/Input";
import PasswordInput from "../../components/ui/PasswordInput";
import Button from "../../components/ui/Button";
import Alert from "../../components/ui/Alert";
import { useAuth } from "../../hooks/useAuth";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const redirectTo = location.state?.from?.pathname || "/";

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ email, password });
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err.message || "Incorrect email or password. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthLayout
      heroEyebrow="Intelligent Government Service & Business Support"
      heroTitle="Empowering MSMEs with smarter access to government services."
      heroLede="One profile. Smarter access to schemes, registrations and support designed around how your business actually works."
      heroFooter="Secure Government Service Platform · Your information is protected"
    >
      <h2 className="mb-1.5 text-[22px]">Sign in to your profile</h2>
      <p className="mb-7 text-sm text-ink-500">Access your business profile and government service recommendations.</p>

      <form onSubmit={handleSubmit} noValidate>
        <Alert variant="error" className="mb-5">
          {error}
        </Alert>

        <Input
          label="Email address"
          required
          type="email"
          autoComplete="email"
          placeholder="you@business.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          containerClassName="mb-[18px]"
        />
        <PasswordInput
          label="Password"
          required
          autoComplete="current-password"
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <div className="mb-5 mt-5 flex items-center justify-between">
          <label className="flex items-center gap-2 text-[13.5px] text-ink-700">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="h-4 w-4 accent-teal-600"
            />
            Remember me
          </label>
          <span className="cursor-not-allowed text-[13.5px] font-semibold text-teal-600/60" title="Coming soon">
            Forgot password?
          </span>
        </div>

        <Button type="submit" fullWidth isLoading={isSubmitting}>
          Sign In
        </Button>

        <div className="my-6 flex items-center gap-3 font-data text-xs text-ink-400">
          <span className="h-px flex-1 bg-border" /> OR <span className="h-px flex-1 bg-border" />
        </div>

        <Link to="/register">
          <Button type="button" variant="secondary" fullWidth>
            Create MSME Profile
          </Button>
        </Link>

        <div className="mt-5 flex items-start gap-2.5 rounded-md border border-border bg-surface-sunken px-3.5 py-3 text-[12.5px] leading-relaxed text-ink-500">
          <svg width="16" height="16" className="mt-0.5 flex-shrink-0" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L4 5v6c0 5 3.4 9 8 11 4.6-2 8-6 8-11V5l-8-3z" stroke="#5B6E80" strokeWidth="1.6" />
          </svg>
          This is a secure government-aligned digital service. Your credentials are encrypted and never shared with third parties.
        </div>
      </form>
    </AuthLayout>
  );
}
