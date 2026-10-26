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

  const redirectTo = location.state?.from?.pathname || "/profile/completed";

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
      mode="login"
      heroTitle="Welcome Back"
      heroLede="Sign in to access your personalized dashboard and scheme recommendations."
      heroFooter="Stronger MSMEs, a brighter India."
      imageSrc="/images/artisan.jpg"
    >
      <div className="mb-6">
        <h2 className="text-2xl font-extrabold text-charcoal">Login to MSMEAssist</h2>
        <p className="mt-1 text-xs text-slate-text">
          Enter your registered email address or mobile number to continue.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {error && (
          <Alert variant="error">
            {error}
          </Alert>
        )}

        <Input
          label="Email or Mobile Number"
          required
          type="email"
          autoComplete="email"
          placeholder="Enter your email or mobile number"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <PasswordInput
          label="Password"
          required
          autoComplete="current-password"
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <div className="flex items-center justify-between pt-1">
          <label className="flex items-center gap-2 text-xs font-medium text-slate-dark cursor-pointer">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="h-4 w-4 rounded accent-burnt-orange border-border"
            />
            <span>Remember me</span>
          </label>
          <span className="text-xs font-semibold text-slate-text hover:text-burnt-orange cursor-pointer">
            Forgot password?
          </span>
        </div>

        <div className="pt-2">
          <Button type="submit" variant="primary" fullWidth size="lg" isLoading={isSubmitting} className="font-bold">
            Login
          </Button>
        </div>

        <div className="pt-4 text-center text-xs text-slate-text">
          Don't have an account?{" "}
          <Link to="/register" className="font-bold text-burnt-orange hover:underline">
            Register
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
}
