import { useState, useEffect, useCallback, useRef } from 'react';
import { useProfile, useUpdateProfile } from '../api/profile';
import ProfileForm from '../components/forms/ProfileForm';
import LoadingSpinner from '../components/common/LoadingSpinner';
import EmptyState from '../components/common/EmptyState';
import ErrorState from '../components/common/ErrorState';
import type { UserProfile } from '../types';
import styles from './ProfilePage.module.css';

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

const EMPTY_PROFILE: UserProfile = {
  name: '',
  email: '',
  phone: '',
  location: '',
  links: {},
  education: [],
  experience: [],
  personal_projects: [],
  publications: [],
  skills: { languages: [], frameworks: [], tools: [], domains: [] },
  certifications: [],
  leadership: [],
  custom_sections: [],
  section_order: [],
  subjective_profile_path: '',
  subjective_profile_content: '',
};

const ProfilePage = () => {
  const { data: fetchedProfile, isLoading, isError, error, refetch } = useProfile();
  const updateProfile = useUpdateProfile();

  const [editableProfile, setEditableProfile] = useState<UserProfile | null>(null);
  const [originalProfile, setOriginalProfile] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const revertTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  /* ── Initialise editable state when fetched data arrives ── */
  useEffect(() => {
    if (fetchedProfile) {
      const clone = JSON.parse(JSON.stringify(fetchedProfile)) as UserProfile;
      setEditableProfile(clone);
      setOriginalProfile(JSON.stringify(clone));
    }
  }, [fetchedProfile]);

  /* ── Cleanup the auto-revert timer on unmount ── */
  useEffect(() => {
    return () => {
      if (revertTimerRef.current) clearTimeout(revertTimerRef.current);
    };
  }, []);

  /* ── Derived state ── */
  const isDirty =
    editableProfile !== null &&
    originalProfile !== null &&
    JSON.stringify(editableProfile) !== originalProfile;

  /* ── Handlers ── */
  const handleChange = useCallback((updated: UserProfile) => {
    setEditableProfile(updated);
  }, []);

  const handleSave = async () => {
    if (!editableProfile) return;
    setSaveStatus('saving');
    try {
      await updateProfile.mutateAsync(editableProfile);
      const serialised = JSON.stringify(editableProfile);
      setOriginalProfile(serialised);
      setSaveStatus('saved');
      revertTimerRef.current = setTimeout(() => setSaveStatus('idle'), 2000);
    } catch {
      setSaveStatus('error');
    }
  };

  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  const handleCreateEmpty = useCallback(() => {
    const clone = JSON.parse(JSON.stringify(EMPTY_PROFILE)) as UserProfile;
    setEditableProfile(clone);
    setOriginalProfile(JSON.stringify(clone));
  }, []);

  /* ── Loading state ── */
  if (isLoading) {
    return (
      <div className={styles.page}>
        <LoadingSpinner message="Loading profile…" size="lg" />
      </div>
    );
  }

  /* ── Error state ── */
  if (isError) {
    return (
      <div className={styles.page}>
        <ErrorState
          message={error instanceof Error ? error.message : 'Failed to load profile'}
          onRetry={handleRetry}
        />
      </div>
    );
  }

  /* ── Empty / not-found state ── */
  if (fetchedProfile === null && !editableProfile) {
    return (
      <div className={styles.page}>
        <EmptyState
          title="No profile found"
          description="Create a profile to start generating tailored resumes."
          actionLabel="Create one"
          onAction={handleCreateEmpty}
        />
      </div>
    );
  }

  /* ── Main view ── */
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Your Profile</h1>

        <button
          className={`${styles.saveBtn} ${styles[saveStatus]}`}
          onClick={handleSave}
          disabled={!isDirty || saveStatus === 'saving'}
          type="button"
        >
          {saveStatus === 'saving' && (
            <>
              <span className={styles.btnSpinner} aria-hidden="true" />
              Saving…
            </>
          )}
          {saveStatus === 'saved' && <>Saved ✓</>}
          {saveStatus === 'error' && <>Error — Retry</>}
          {saveStatus === 'idle' && 'Save Profile'}
        </button>
      </header>

      <div className={styles.formWrapper}>
        {editableProfile && (
          <ProfileForm
            profile={editableProfile}
            onChange={handleChange}
          />
        )}
      </div>
    </div>
  );
};

export default ProfilePage;
