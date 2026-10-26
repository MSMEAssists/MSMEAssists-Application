import { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as profileService from "../services/profileService";
import * as documentService from "../services/documentService";

const OnboardingContext = createContext(null);

export function OnboardingProvider({ children }) {
  const [profile, setProfile] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const loadProfile = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [profileData, documentList] = await Promise.all([
        profileService.getMyProfileOrNull(),
        documentService.listDocuments().catch(() => []),
      ]);
      setProfile(profileData);
      setDocuments(documentList);
    } catch (err) {
      setLoadError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  /**
   * Saves one wizard section. Uses POST for the very first save (no
   * profile exists yet — only valid for the `business` step, since that's
   * the only section the backend accepts on create) and PUT thereafter.
   */
  const saveSection = useCallback(
    async (sectionPayload) => {
      setIsSaving(true);
      try {
        const updated = profile
          ? await profileService.updateProfile(sectionPayload)
          : await profileService.createProfile(sectionPayload);
        setProfile(updated);
        return updated;
      } finally {
        setIsSaving(false);
      }
    },
    [profile]
  );

  const refreshDocuments = useCallback(async () => {
    const list = await documentService.listDocuments();
    setDocuments(list);
    return list;
  }, []);

  /** Re-fetches the profile so completeness reflects document changes (uploads/deletes affect the `documents` section server-side). */
  const refreshCompleteness = useCallback(async () => {
    const updated = await profileService.getMyProfileOrNull();
    setProfile(updated);
    return updated;
  }, []);

  const uploadDocument = useCallback(
    async (args, opts) => {
      const doc = await documentService.uploadDocument(args, opts);
      await refreshDocuments();
      await refreshCompleteness();
      return doc;
    },
    [refreshDocuments, refreshCompleteness]
  );

  const removeDocument = useCallback(
    async (documentId) => {
      await documentService.deleteDocument(documentId);
      await refreshDocuments();
      await refreshCompleteness();
    },
    [refreshDocuments, refreshCompleteness]
  );

  const value = {
    profile,
    documents,
    isLoading,
    isSaving,
    loadError,
    hasProfile: profile !== null,
    completeness: profile?.completeness ?? { percentage: 0, sections: {} },
    saveSection,
    refreshDocuments,
    refreshCompleteness,
    uploadDocument,
    removeDocument,
    reload: loadProfile,
  };

  return <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>;
}

export function useOnboarding() {
  const ctx = useContext(OnboardingContext);
  if (!ctx) throw new Error("useOnboarding must be used within an OnboardingProvider");
  return ctx;
}
