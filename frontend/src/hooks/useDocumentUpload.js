import { useCallback, useState } from "react";
import { useOnboarding } from "../context/OnboardingContext";

export function useDocumentUpload() {
  const { documents, uploadDocument, removeDocument } = useOnboarding();
  const [pending, setPending] = useState({}); // { [tempId]: { fileName, progress, error } }

  const upload = useCallback(
    async (documentType, file) => {
      const tempId = `${file.name}-${Date.now()}`;
      setPending((prev) => ({ ...prev, [tempId]: { fileName: file.name, progress: 0, error: null } }));
      try {
        await uploadDocument(
          { documentType, file },
          {
            onProgress: (pct) =>
              setPending((prev) => ({ ...prev, [tempId]: { ...prev[tempId], progress: pct } })),
          }
        );
        setPending((prev) => {
          const next = { ...prev };
          delete next[tempId];
          return next;
        });
      } catch (err) {
        setPending((prev) => ({
          ...prev,
          [tempId]: { ...prev[tempId], error: err.message || "Upload failed" },
        }));
        throw err;
      }
    },
    [uploadDocument]
  );

  const remove = useCallback((documentId) => removeDocument(documentId), [removeDocument]);

  return { documents, pendingUploads: Object.values(pending), upload, remove };
}
