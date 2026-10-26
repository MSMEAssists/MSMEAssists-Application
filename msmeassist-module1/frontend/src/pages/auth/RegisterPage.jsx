import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "../../layouts/AuthLayout";
import Input from "../../components/ui/Input";
import PasswordInput from "../../components/ui/PasswordInput";
import Button from "../../components/ui/Button";
import Alert from "../../components/ui/Alert";
import { useAuth } from "../../hooks/useAuth";
import { isValidEmail, isValidMobile, passwordMeetsMinimum } from "../../utils/validators";

const INITIAL_FORM = { fullName: "", email: "", mobileNumber: "", password: "", confirmPassword: "" };

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState(INITIAL_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState(null);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function validate() {
    const errors = {};
    if (!form.fullName.trim()) errors.fullName = "Full name is required";
    if (!isValidEmail(form.email)) errors.email = "Enter a valid email address";
    if (!isValidMobile(form.mobileNumber)) errors.mobileNumber = "Enter a valid number, e.g. +919845012345";
    if (!passwordMeetsMinimum(form.password)) errors.password = "At least 8 characters, with a letter and a digit";
    if (form.password !== form.confirmPassword) errors.confirmPassword = "Passwords do not match";
    if (!agreedToTerms) errors.terms = "You must agree to the Terms of Service and Privacy Policy";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setApiError(null);
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await register(form);
      navigate("/onboarding/business", { replace: true });
    } catch (err) {
      if (err.field) {
        setFieldErrors((prev) => ({ ...prev, [toCamel(err.field)]: err.message }));
      } else {
        setApiError(err.message || "Something went wrong while creating your account.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthLayout
      mode="register"
      heroTitle="Build one profile. Unlock every scheme."
      imageSrc="/images/woman_entrepreneur.jpg"
    >
      <div className="mb-6">
        <h2 className="text-2xl font-extrabold text-charcoal">Create Your Account</h2>
        <p className="mt-1 text-xs text-slate-text">
          Join MSMEAssist to get personalized scheme recommendations and expert guidance.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-3.5">
        {apiError && <Alert variant="error">{apiError}</Alert>}

        <Input
          label="Full Name"
          required
          placeholder="Enter your full name"
          value={form.fullName}
          error={fieldErrors.fullName}
          onChange={(e) => update("fullName", e.target.value)}
        />
        <Input
          label="Email Address"
          required
          type="email"
          autoComplete="email"
          placeholder="Enter your email address"
          value={form.email}
          error={fieldErrors.email}
          onChange={(e) => update("email", e.target.value)}
        />
        <Input
          label="Mobile Number"
          required
          placeholder="Enter your mobile number"
          hint={!fieldErrors.mobileNumber ? "Format: +91XXXXXXXXXX" : undefined}
          value={form.mobileNumber}
          error={fieldErrors.mobileNumber}
          onChange={(e) => update("mobileNumber", e.target.value)}
        />
        <PasswordInput
          label="Password"
          required
          autoComplete="new-password"
          placeholder="Create a strong password"
          showStrength
          value={form.password}
          error={fieldErrors.password}
          onChange={(e) => update("password", e.target.value)}
        />
        <PasswordInput
          label="Confirm Password"
          required
          autoComplete="new-password"
          placeholder="Re-enter your password"
          value={form.confirmPassword}
          error={fieldErrors.confirmPassword}
          onChange={(e) => update("confirmPassword", e.target.value)}
        />

        <div className="pt-1">
          <label className="flex items-start gap-2 text-xs text-slate-dark cursor-pointer">
            <input
              type="checkbox"
              checked={agreedToTerms}
              onChange={(e) => setAgreedToTerms(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded accent-burnt-orange border-border"
            />
            <span>
              I agree to the{" "}
              <span className="font-semibold text-burnt-orange hover:underline">Terms of Service</span> and{" "}
              <span className="font-semibold text-burnt-orange hover:underline">Privacy Policy</span>
            </span>
          </label>
          {fieldErrors.terms && <p className="mt-1 text-[12px] font-medium text-error-600">{fieldErrors.terms}</p>}
        </div>

        <div className="pt-2">
          <Button type="submit" variant="primary" fullWidth size="lg" isLoading={isSubmitting} className="font-bold">
            Register
          </Button>
        </div>

        <div className="pt-3 text-center text-xs text-slate-text">
          Already have an account?{" "}
          <Link to="/login" className="font-bold text-burnt-orange hover:underline">
            Login
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
}

function toCamel(snake) {
  return snake.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}
