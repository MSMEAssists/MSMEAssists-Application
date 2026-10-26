import { FiFile, FiImage, FiRefreshCw, FiX } from "react-icons/fi";
import Badge from "../ui/Badge";
import { DOCUMENT_STATUS_LABEL } from "../../utils/constants";
import { formatBytes } from "../../utils/formatters";

const STATUS_BADGE_VARIANT = {
  uploading: "neutral",
  uploaded: "success",
  pending_review: "warning",
  verified: "success",
  rejected: "error",
};

export function DocumentCard({ document, onDelete, isDeleting }) {
  const Icon = document.mime_type === "application/pdf" ? FiFile : FiImage;
  const isRejected = document.status === "rejected";

  return (
    <div className="mb-2.5 flex items-center gap-3.5 rounded-md border border-border bg-white px-4 py-3.5">
      <div
        className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${
          isRejected ? "bg-error-100 text-error-600" : "bg-surface-sunken text-navy-800"
        }`}
      >
        <Icon size={17} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[13.5px] font-semibold text-ink-900">{document.file_name}</div>
        <div className="mt-0.5 font-data text-[11.5px] text-ink-400">
          {isRejected
            ? document.rejection_reason || "Rejected — document illegible"
            : `${document.mime_type === "application/pdf" ? "PDF" : "Image"} · ${formatBytes(document.size_bytes)}`}
        </div>
      </div>
      <Badge variant={STATUS_BADGE_VARIANT[document.status] || "neutral"}>
        {DOCUMENT_STATUS_LABEL[document.status] || document.status}
      </Badge>
      <div className="flex flex-shrink-0 gap-1.5">
        <button
          type="button"
          onClick={() => onDelete(document.id)}
          disabled={isDeleting}
          aria-label="Remove document"
          className="flex h-[30px] w-[30px] items-center justify-center rounded-md border border-border bg-white text-ink-500 hover:bg-surface-sunken hover:text-ink-900 disabled:opacity-50"
        >
          <FiX size={14} />
        </button>
      </div>
    </div>
  );
}

export function PendingUploadCard({ upload }) {
  return (
    <div className="mb-2.5 flex items-center gap-3.5 rounded-md border border-border bg-white px-4 py-3.5">
      <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-surface-sunken text-navy-800">
        <FiRefreshCw size={16} className={upload.error ? "" : "animate-spin"} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[13.5px] font-semibold text-ink-900">{upload.fileName}</div>
        {upload.error ? (
          <div className="mt-0.5 text-[11.5px] font-medium text-error-600">{upload.error}</div>
        ) : (
          <>
            <div className="mt-0.5 font-data text-[11.5px] text-ink-400">Uploading… {upload.progress}%</div>
            <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-surface-sunken">
              <div
                className="h-full rounded-full bg-teal-500 transition-all"
                style={{ width: `${upload.progress}%` }}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
