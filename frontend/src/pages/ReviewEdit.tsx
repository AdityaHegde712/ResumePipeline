import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApplication } from '../api/history';
import LoadingSpinner from '../components/common/LoadingSpinner';
import EmptyState from '../components/common/EmptyState';
import ErrorState from '../components/common/ErrorState';
import StatusBadge from '../components/common/StatusBadge';
import BulletEditor from '../components/generation/BulletEditor';
import ProgressPanel from '../components/generation/ProgressPanel';
import type { BulletPoint, SectionPoints } from '../types';
import styles from './ReviewEdit.module.css';

const RESUME_STAGES = ['keyword_analysis', 'matching', 'generating_points', 'writing_resume', 'rendering_latex'];

export default function ReviewEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: app, isLoading, isError, error, refetch } = useApplication(id);

  const [activeSection, setActiveSection] = useState('');
  const [customInstructions, setCustomInstructions] = useState('');
  const [regenerating, setRegenerating] = useState(false);
  const [genOverlay, setGenOverlay] = useState(false);
  const [genStage, setGenStage] = useState('');
  const [genMessage, setGenMessage] = useState('');
  const [genTokens, setGenTokens] = useState('');

  const sections: SectionPoints[] = app?.generated?.resume_points ?? [];
  const activeBullets: BulletPoint[] = sections.find((s) => s.section_key === activeSection)?.bullets ?? [];

  useEffect(() => {
    if (sections.length > 0 && !activeSection) {
      setActiveSection(sections[0].section_key);
    }
  }, [sections, activeSection]);

  const updateBullet = (_bulletId: string, _text: string) => {
    refetch();
  };

  const deleteBullet = (_bulletId: string) => {
    refetch();
  };

  const moveBullet = (_bulletId: string) => {
    refetch();
  };

  const handleRegenerate = async () => {
    if (!id || !activeSection) return;
    setRegenerating(true);
    // Simulate regeneration — in real implementation, streamRegenerateSection would be called
    setTimeout(() => {
      refetch();
      setRegenerating(false);
    }, 1000);
  };

  const handleGenerateResume = () => {
    setGenOverlay(true);
    setGenStage('keyword_analysis');
    setGenMessage('Analyzing keywords...');
    setGenTokens('');

    // For now, simulate stages then navigate
    const stages = RESUME_STAGES;
    stages.forEach((stage, i) => {
      setTimeout(() => {
        setGenStage(stage);
        setGenMessage(`Running ${stage.replace(/_/g, ' ')}...`);
        if (stage === 'rendering_latex') {
          setTimeout(() => {
            setGenMessage('');
            navigate(`/export/${id}`);
          }, 1000);
        }
      }, (i + 1) * 1500);
    });
  };

  if (isLoading) return <LoadingSpinner message="Loading application..." />;
  if (isError) return <ErrorState message={(error as Error)?.message || 'Failed to load'} onRetry={() => refetch()} />;
  if (!app) return <ErrorState message="Application not found" />;

  if (sections.length === 0) {
    return (
      <EmptyState
        title="No generated content"
        description={app.generation_status === 'failed' ? app.error_message || 'Generation failed' : 'Generate bullet points first'}
        actionLabel="New Application"
        onAction={() => navigate('/new')}
      />
    );
  }

  const totalBullets = sections.reduce((sum, sec) => sum + sec.bullets.length, 0);

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerInfo}>
          <h1>{app.company_name} — {app.job_title}</h1>
          <button className={styles.backLink} onClick={() => navigate('/')}>← Back to Dashboard</button>
        </div>
        <StatusBadge status={app.generation_status} />
      </div>

      {/* Tabs */}
      <div className={styles.tabs}>
        {sections.map((sec) => (
          <button
            key={sec.section_key}
            className={`${styles.tab} ${activeSection === sec.section_key ? styles.active : ''}`}
            onClick={() => setActiveSection(sec.section_key)}
          >
            {sec.section_title}
          </button>
        ))}
      </div>

      {/* Active section */}
      {activeBullets.length === 0 ? (
        <div className={styles.emptySection}>No bullet points for this section</div>
      ) : (
        <div>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>{sections.find((s) => s.section_key === activeSection)?.section_title}</h2>
          </div>

          {activeBullets.map((bullet, i) => (
            <BulletEditor
              key={bullet.id}
              bullet={bullet}
              onUpdate={updateBullet}
              onDelete={deleteBullet}
              onMoveUp={moveBullet}
              onMoveDown={moveBullet}
              isFirst={i === 0}
              isLast={i === activeBullets.length - 1}
            />
          ))}

          <textarea
            className={styles.instructionInput}
            placeholder="Optional: specific instructions for regeneration..."
            value={customInstructions}
            onChange={(e) => setCustomInstructions(e.target.value)}
          />
          <button className={styles.regenBtn} onClick={handleRegenerate} disabled={regenerating}>
            {regenerating ? 'Regenerating...' : 'Regenerate Section'}
          </button>
        </div>
      )}

      {/* Bottom bar */}
      <div className={styles.bottomBar}>
        <span className={styles.bulletCount}>{totalBullets} bullets across {sections.length} sections</span>
        <button className={styles.generateBtn} onClick={handleGenerateResume}>
          Generate Full Resume
        </button>
      </div>

      {/* Generation overlay */}
      {genOverlay && (
        <div className={styles.overlay}>
          <div className={styles.overlayContent}>
            <ProgressPanel
              stages={RESUME_STAGES}
              currentStage={genStage}
              statusMessage={genMessage}
              tokenStream={genTokens}
            />
          </div>
        </div>
      )}
    </div>
  );
}
