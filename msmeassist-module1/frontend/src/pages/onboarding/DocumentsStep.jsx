import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Select from "../../components/ui/Select";
import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import WizardNav from "../../components/wizard/WizardNav";
import { PageLoader } from "../../components/ui/Spinner";
import UploadZone from "../../components/documents/UploadZone";
import { DocumentCard, PendingUploadCard } from "../../components/documents/DocumentCard";
import { useOnboarding } from "../../context/OnboardingContext";
import { useDocumentUpload } from "../../hooks/useDocumentUpload";
import { DOCUMENT_TYPES, ALLOWED_DOCUMENT_MIME_TYPES, MAX_UPLOAD_SIZE_MB } from "../../utils/constants";

export default function DocumentsStep() {
  const { profile, isLoading } = useOnboarding();
  const { documents, pendingUploads, upload, remove } = useDocumentUpload();
  const navigate = useNavigate();

  const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0].value);
  const [apiError, setApiError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  async function handleFiles(files) {
    setApiError(null);
    for (const file of files) {
      if (!ALLOWED_DOCUMENT_MIME_TYPES.includes(file.type)) {
        setApiError(`${file.name}: only PDF, JPG, JPEG or PNG files are accepted.`);
        continue;
      }
      if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
        setApiError(`${file.name}: file exceeds the ${MAX_UPLOAD_SIZE_MB}MB upload limit.`);
        continue;
      }
      try {
        await upload(documentType, file);
      } catch (err) {
        setApiError(err.message || `Could not upload ${file.name}.`);
      }
    }
  }

  async function handleDelete(documentId) {
    setDeletingId(documentId);
    try {
      await remove(documentId);
    } catch (err) {
      setApiError(err.message || "Could not remove this document.");
    } finally {
      setDeletingId(null);
    }
  }

  function goNext() {
    navigate("/onboarding/review");
  }

  if (isLoading) return <PageLoader label="Loading…" />;

  if (!profile) {
    return (
      <div>
        <Alert variant="warning">Please complete the Business step before uploading documents.</Alert>
        <WizardNav stepKey="documents" onSaveAndExit={() => navigate("/")} continueLabel="Continue →" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl sm:text-2xl font-extrabold text-charcoal">6. Supporting Documents</h2>
        <p className="mt-1 text-xs sm:text-sm text-slate-text">
          Upload official business documentation (PDF, JPG, PNG) to accelerate scheme eligibility checks.
        </p>
      </div>

      <Alert variant="error" className="mb-5">{apiError}</Alert>

      <Select
        label="Document type for the next upload"
        options={DOCUMENT_TYPES}
        value={documentType}
        onChange={(e) => setDocumentType(e.target.value)}
        containerClassName="mb-5 max-w-sm"
      />

      <UploadZone onFilesSelected={handleFiles} />

      {pendingUploads.map((u, i) => (
        <PendingUploadCard key={i} upload={u} />
      ))}

      {documents.length === 0 && pendingUploads.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border bg-warm-offwhite/60 px-4 py-8 text-center text-xs text-slate-text">
          No documents uploaded yet. You can also upload them later from your dashboard.
        </p>
      ) : (
        <div className="space-y-3 mt-4">
          {documents.map((doc) => (
            <DocumentCard key={doc.id} document={doc} onDelete={handleDelete} isDeleting={deletingId === doc.id} />
          ))}
        </div>
      )}

      <div className="mt-10 flex items-center justify-between border-t border-border pt-6">
        <Button
          variant="secondary"
          size="md"
          type="button"
          onClick={() => navigate("/onboarding/registrations")}
          className="flex items-center gap-1.5 font-semibold text-slate-dark"
        >
          <span>← Back</span>
        </Button>
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="md"
            type="button"
            onClick={() => navigate("/")}
            className="text-xs font-semibold text-slate-text hover:text-charcoal"
          >
            Save Draft
          </Button>
          <Button type="button" variant="primary" size="md" onClick={goNext} className="font-bold px-6 shadow-sm">
            <span>Next →</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
