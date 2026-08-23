import apiClient from "./apiClient";

export async function listDocuments() {
  const { data } = await apiClient.get("/profile/documents");
  return data.documents;
}

export async function uploadDocument({ documentType, file }, { onProgress } = {}) {
  const formData = new FormData();
  formData.append("document_type", documentType);
  formData.append("file", file);

  const { data } = await apiClient.post("/profile/documents", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded / evt.total) * 100));
      }
    },
  });
  return data;
}

export async function deleteDocument(documentId) {
  await apiClient.delete(`/profile/documents/${documentId}`);
}
