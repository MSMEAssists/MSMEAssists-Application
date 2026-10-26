import { useRef, useState } from "react";
import { FiUploadCloud } from "react-icons/fi";
import { ALLOWED_DOCUMENT_MIME_TYPES, MAX_UPLOAD_SIZE_MB } from "../../utils/constants";

export default function UploadZone({ onFilesSelected, disabled }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = (fileList) => {
    const files = Array.from(fileList).filter((f) => ALLOWED_DOCUMENT_MIME_TYPES.includes(f.type));
    if (files.length) onFilesSelected(files);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      className={[
        "mb-5 cursor-pointer rounded-lg border-2 border-dashed px-6 py-9 text-center transition-colors",
        isDragging ? "border-teal-500 bg-teal-100" : "border-border-strong bg-surface-sunken hover:border-teal-500 hover:bg-teal-100",
        disabled ? "pointer-events-none opacity-60" : "",
      ].join(" ")}
    >
      <FiUploadCloud size={32} className="mx-auto mb-3 text-teal-600" />
      <b className="mb-1 block text-sm text-navy-900">Drag and drop files here, or click to browse</b>
      <span className="text-[12.5px] text-ink-500">
        PDF, JPG, JPEG or PNG · up to {MAX_UPLOAD_SIZE_MB} MB per file
      </span>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ALLOWED_DOCUMENT_MIME_TYPES.join(",")}
        className="hidden"
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
