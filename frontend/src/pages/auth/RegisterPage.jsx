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
      heroEyebrow="Get started in minutes"
      heroTitle="Build one business profile. Unlock every relevant government service."
      heroLede="Your details are used only to assess eligibility and connect you with services suited to your business."
      heroFooter="Your information is used to provide relevant business services."
    >
      <h2 className="mb-1.5 text-[22px]">Create your MSMEAssist account</h2>
      <p className="mb-7 text-sm text-ink-500">Takes about 2 minutes. You'll build your full business profile next.</p>

      <form onSubmit={handleSubmit} noValidate className="space-y-[18px]">
        <Alert variant="error">{apiError}</Alert>

        <Input
          label="Full Name"
          required
          placeholder="As per your ID"
          value={form.fullName}
          error={fieldErrors.fullName}
          onChange={(e) => update("fullName", e.target.value)}
        />
        <Input
          label="Email"
          required
          type="email"
          autoComplete="email"
          placeholder="you@business.com"
          value={form.email}
          error={fieldErrors.email}
          onChange={(e) => update("email", e.target.value)}
        />
        <Input
          label="Mobile Number"
          required
          placeholder="+91 00000 00000"
          hint={!fieldErrors.mobileNumber ? "Format: +91XXXXXXXXXX" : undefined}
          value={form.mobileNumber}
          error={fieldErrors.mobileNumber}
          onChange={(e) => update("mobileNumber", e.target.value)}
        />
        <PasswordInput
          label="Password"
          required
          autoComplete="new-password"
          showStrength
          value={form.password}
          error={fieldErrors.password}
          onChange={(e) => update("password", e.target.value)}
        />
        <PasswordInput
          label="Confirm Password"
          required
          autoComplete="new-password"
          value={form.confirmPassword}
          error={fieldErrors.confirmPassword}
          onChange={(e) => update("confirmPassword", e.target.value)}
        />

        <label className="flex items-start gap-2 text-[13.5px] text-ink-700">
          <input
            type="checkbox"
            checked={agreedToTerms}
            onChange={(e) => setAgreedToTerms(e.target.checked)}
            className="mt-0.5 h-4 w-4 accent-teal-600"
          />
          <span>
            I agree to the{" "}
            <span className="font-semibold text-teal-600">Terms of Service</span> and{" "}
            <span className="font-semibold text-teal-600">Privacy Policy</span>
          </span>
        </label>
        {fieldErrors.terms && <p className="text-[12.5px] font-medium text-error-600">{fieldErrors.terms}</p>}

        <Button type="submit" fullWidth isLoading={isSubmitting}>
          Create Account &amp; Continue
        </Button>

        <div className="flex items-center gap-3 pt-1 font-data text-xs text-ink-400">
          <span className="h-px flex-1 bg-border" /> Already have a profile? <span className="h-px flex-1 bg-border" />
        </div>

        <Link to="/login">
          <Button type="button" variant="secondary" fullWidth>
            Sign In Instead
          </Button>
        </Link>
      </form>
    </AuthLayout>
  );
}

function toCamel(snake) {
  return snake.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}
