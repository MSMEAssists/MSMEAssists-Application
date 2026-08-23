// Mirrors backend/app/core/constants.py — keep enum values identical so
// payloads sent to the API are always valid without client-side translation.

export const BUSINESS_TYPES = [
  { value: "manufacturing", label: "Manufacturing" },
  { value: "services", label: "Services" },
  { value: "trading", label: "Trading" },
  { value: "other", label: "Other" },
];

export const AREA_TYPES = [
  { value: "rural", label: "Rural" },
  { value: "urban", label: "Urban" },
];

export const PREMISES_TYPES = [
  { value: "own", label: "Own Premises" },
  { value: "rented", label: "Rented Premises" },
  { value: "industrial_estate", label: "Industrial Estate / SEZ" },
  { value: "shared", label: "Shared / Co-working Facility" },
];

export const PROFITABILITY_STATUSES = [
  { value: "profitable", label: "Profitable" },
  { value: "break_even", label: "Break-even" },
  { value: "loss", label: "Operating at Loss" },
];

export const SOCIAL_CATEGORIES = [
  { value: "general", label: "General" },
  { value: "sc", label: "Scheduled Caste (SC)" },
  { value: "st", label: "Scheduled Tribe (ST)" },
  { value: "obc", label: "Other Backward Class (OBC)" },
  { value: "other", label: "Other" },
];

export const REGISTRATION_TYPES = [
  { value: "udyam", label: "Udyam Registration" },
  { value: "gst", label: "GST Registration" },
  { value: "pan", label: "PAN" },
  { value: "fssai", label: "FSSAI License" },
  { value: "iec", label: "Import Export Code (IEC)" },
  { value: "factory_license", label: "Factory License" },
  { value: "trade_license", label: "Trade License" },
  { value: "pollution_noc", label: "Pollution Consent / NOC" },
  { value: "other", label: "Other" },
];

export const REGISTRATION_STATUSES = [
  { value: "registered", label: "Registered" },
  { value: "not_registered", label: "Not Registered" },
  { value: "in_progress", label: "In Progress" },
  { value: "not_applicable", label: "Not Applicable" },
];

export const DOCUMENT_TYPES = [
  { value: "udyam_certificate", label: "Udyam Certificate" },
  { value: "gst_certificate", label: "GST Certificate" },
  { value: "pan_card", label: "PAN Card" },
  { value: "factory_license", label: "Factory License" },
  { value: "trade_license", label: "Trade License" },
  { value: "other", label: "Other Document" },
];

export const DOCUMENT_STATUS_LABEL = {
  uploading: "Uploading",
  uploaded: "Uploaded",
  pending_review: "Pending Review",
  verified: "Verified",
  rejected: "Rejected",
};

export const REGISTRATION_STATUS_BADGE = {
  registered: "success",
  in_progress: "warning",
  not_registered: "error",
  not_applicable: "neutral",
};

export const WIZARD_STEPS = [
  { key: "business", label: "Business", index: 1 },
  { key: "location", label: "Location", index: 2 },
  { key: "financial", label: "Financial", index: 3 },
  { key: "characteristics", label: "Characteristics", index: 4 },
  { key: "registrations", label: "Registrations", index: 5 },
  { key: "documents", label: "Documents", index: 6 },
  { key: "review", label: "Review", index: 7 },
];

export const ALLOWED_DOCUMENT_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png"];
export const MAX_UPLOAD_SIZE_MB = 10;
