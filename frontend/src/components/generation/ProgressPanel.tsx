import { useRef, useEffect } from 'react';
import styles from './ProgressPanel.module.css';

export interface ProgressPanelProps {
  stages: string[];
  currentStage: string;
  statusMessage: string;
  tokenStream: string;
  sectionProgress?: {
    section: string;
    index: number;
    total: number;
  };
}

function formatStageLabel(stage: string): string {
  return stage
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function ProgressPanel({
  stages,
  currentStage,
  statusMessage,
  tokenStream,
  sectionProgress,
}: ProgressPanelProps) {
  const tokenContainerRef = useRef<HTMLDivElement>(null);

  /* Auto-scroll token stream to bottom on new tokens */
  useEffect(() => {
    const el = tokenContainerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [tokenStream]);

  const currentIdx = stages.indexOf(currentStage);

  return (
    <div className={styles.panel}>
      {/* ── Stage dots ── */}
      <div className={styles.stagesRow}>
        {stages.map((stage, i) => {
          const isCompleted = i < currentIdx;
          const isCurrent = i === currentIdx;

          const dotClass = [
            styles.stageDot,
            isCompleted ? styles.completed : isCurrent ? styles.current : styles.pending,
          ]
            .join(' ');

          const connectorClass =
            i < stages.length - 1
              ? [styles.stageConnector, isCompleted ? styles.completed : styles.pending].join(' ')
              : null;

          return (
            <div key={stage} className={styles.stageItem}>
              <div className={dotClass}>
                {isCompleted ? (
                  <span className={styles.checkIcon}>✓</span>
                ) : (
                  <span>{i + 1}</span>
                )}
              </div>
              {connectorClass && <div className={connectorClass} />}
            </div>
          );
        })}
      </div>

      {/* ── Stage labels ── */}
      <div className={styles.stageLabels}>
        {stages.map((stage, i) => {
          const labelClass = [
            styles.stageLabel,
            i < currentIdx ? styles.completed : i === currentIdx ? styles.current : '',
          ]
            .filter(Boolean)
            .join(' ');

          return (
            <div key={stage} className={labelClass}>
              {formatStageLabel(stage)}
            </div>
          );
        })}
      </div>

      {/* ── Status message ── */}
      <div className={styles.statusMessage}>{statusMessage}</div>

      {/* ── Section progress (optional) ── */}
      {sectionProgress && (
        <div className={styles.sectionProgress}>
          <span>
            {sectionProgress.section}: {sectionProgress.index + 1} / {sectionProgress.total}
          </span>
          <div className={styles.sectionProgressBar}>
            <div
              className={styles.sectionProgressFill}
              style={{
                width: `${((sectionProgress.index + 1) / sectionProgress.total) * 100}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* ── Token stream ── */}
      <div>
        <div className={styles.tokenStreamLabel}>Live Output</div>
        <div ref={tokenContainerRef} className={styles.tokenStreamContainer}>
          {tokenStream}
        </div>
      </div>
    </div>
  );
}

export default ProgressPanel;
