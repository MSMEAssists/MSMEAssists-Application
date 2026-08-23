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
      <div className="mb-2 font-data text-xs font-semibold uppercase tracking-wide text-teal-600">Step 6 of 7</div>
      <h3 className="mb-1.5 text-2xl">Upload supporting documents</h3>
      <p className="mb-7 text-sm text-ink-500">
        Accepted formats: PDF, JPG, JPEG, PNG. This step only stores your files — verification happens separately.
      </p>

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
        <p className="rounded-md bg-surface-sunken px-4 py-6 text-center text-[13px] text-ink-400">
          No documents uploaded yet.
        </p>
      ) : (
        documents.map((doc) => (
          <DocumentCard key={doc.id} document={doc} onDelete={handleDelete} isDeleting={deletingId === doc.id} />
        ))
      )}

      <div className="mt-8 flex items-center justify-between border-t border-border pt-6">
        <Button variant="ghost" type="button" onClick={() => navigate("/onboarding/registrations")}>
          ← Back
        </Button>
        <div className="flex gap-2.5">
          <Button variant="ghost" type="button" onClick={() => navigate("/")}>
            Save &amp; Exit
          </Button>
          <Button type="button" onClick={goNext}>
            Continue →
          </Button>
        </div>
      </div>
    </div>
  );
}
