import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProjects, useMatchProjects } from '../api/projects';
import { streamGeneratePoints } from '../api/resume';
import ApplicationForm from '../components/forms/ApplicationForm';
import LoadingSpinner from '../components/common/LoadingSpinner';
import EmptyState from '../components/common/EmptyState';
import ErrorState from '../components/common/ErrorState';
import ProgressPanel from '../components/generation/ProgressPanel';
import type { GenerationRequest, MatchResult } from '../types';
import styles from './NewApplication.module.css';

type PageState = 'idle' | 'generating' | 'error';

const STAGES = ['matching', 'generating_points', 'writing_resume', 'rendering_latex'];

export default function NewApplication() {
  const navigate = useNavigate();
  const { data: projects, isLoading: projLoading, isError: projError, error: projErr, refetch: refetchProj } = useProjects();
  const matchProjects = useMatchProjects();

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [matchResults, _setMatchResults] = useState<MatchResult[]>([]);
  const [pageState, setPageState] = useState<PageState>('idle');
  const [genStage, setGenStage] = useState('');
  const [genMessage, setGenMessage] = useState('');
  const [genTokens, setGenTokens] = useState('');
  const [genError, setGenError] = useState('');

  const filtered = projects
    ? projects.filter(
        (p) =>
          !search ||
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          p.tech_stack.some((t) => t.toLowerCase().includes(search.toLowerCase())) ||
          p.domains.some((d) => d.toLowerCase().includes(search.toLowerCase()))
      )
    : [];

  const toggleProject = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const getRelevance = (projectId: string): number | null => {
    const result = matchResults.find((r) => r.project_id === projectId);
    return result ? result.relevance_score : null;
  };

  const handleGenerate = async (data: GenerationRequest) => {
    if (selectedIds.length === 0) return;
    setPageState('generating');
    setGenTokens('');
    setGenError('');

    await streamGeneratePoints(
      { ...data, selected_project_ids: selectedIds },
      {
        onStage: (stage, message) => {
          setGenStage(stage);
          setGenMessage(message);
        },
        onToken: (text) => setGenTokens((prev) => prev + text),
        onError: (err) => {
          setGenError(err);
          setPageState('error');
        },
        onComplete: (result) => {
          const appId = (result as Record<string, unknown>)?.application_id as string;
          if (appId) navigate(`/review/${appId}`);
        },
      }
    );
  };

  if (pageState === 'generating') {
    return (
      <div className={styles.generationOverlay}>
        <ProgressPanel
          stages={STAGES}
          currentStage={genStage}
          statusMessage={genMessage}
          tokenStream={genTokens}
        />
      </div>
    );
  }

  if (pageState === 'error') {
    return <ErrorState message={genError || 'Generation failed'} onRetry={() => setPageState('idle')} />;
  }

  return (
    <div className={styles.container}>
      <div className={styles.formPanel}>
        <ApplicationForm onSubmit={handleGenerate} loading={false} />
      </div>

      <div className={styles.selectionPanel}>
        <div className={styles.selectionHeader}>
          <h2 className={styles.selectionTitle}>Select Projects</h2>
          <span className={styles.selectionCount}>{selectedIds.length} / {projects?.length ?? 0} selected</span>
        </div>

        <input
          className={styles.searchInput}
          type="text"
          placeholder="Search by name, tech, or domain..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <button
          className={styles.matchBtn}
          disabled={matchProjects.isPending}
          onClick={() => {
            // We'll match using form data stored in ApplicationForm internal state
            // For now, this is a best-effort — the form submits are handled separately
          }}
        >
          {matchProjects.isPending ? 'Matching...' : 'Match to Job'}
        </button>

        {projLoading ? (
          <LoadingSpinner message="Loading projects..." />
        ) : projError ? (
          <ErrorState message={(projErr as Error)?.message || 'Failed to load projects'} onRetry={() => refetchProj()} />
        ) : filtered.length === 0 ? (
          <EmptyState title={search ? 'No matches' : 'No projects'} description={search ? 'Try a different search' : 'Run a sweep to populate projects'} />
        ) : (
          <div className={styles.projectList}>
            {filtered.map((project) => {
              const rel = getRelevance(project.id);
              return (
                <div
                  key={project.id}
                  className={`${styles.projectCard} ${selectedIds.includes(project.id) ? styles.selected : ''}`}
                  onClick={() => toggleProject(project.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && toggleProject(project.id)}
                >
                  <input
                    type="checkbox"
                    className={styles.checkbox}
                    checked={selectedIds.includes(project.id)}
                    onChange={() => toggleProject(project.id)}
                    onClick={(e) => e.stopPropagation()}
                  />
                  <div className={styles.projectInfo}>
                    <div className={styles.projectName}>{project.name}</div>
                    <div className={styles.projectMeta}>
                      <span className={styles.typeBadge}>{project.type}</span>
                      {project.tech_stack.slice(0, 3).map((t) => (
                        <span key={t} className={styles.techPill}>{t}</span>
                      ))}
                    </div>
                    <div className={styles.projectSummary}>{project.summary}</div>
                  </div>
                  {rel !== null && (
                    <span className={`${styles.relevanceBadge} ${rel >= 0.7 ? styles.relevanceHigh : rel >= 0.4 ? styles.relevanceMid : styles.relevanceLow}`}>
                      {(rel * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
