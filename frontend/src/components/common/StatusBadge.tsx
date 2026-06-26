import styles from './StatusBadge.module.css';

interface StatusBadgeProps {
  status: string;
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  matching: 'Matching',
  generating_points: 'Generating Points',
  writing_resume: 'Writing Resume',
  rendering_latex: 'Rendering LaTeX',
  completed: 'Completed',
  failed: 'Failed',
};

const STATUS_STYLE: Record<string, string> = {
  pending: styles.info,
  matching: styles.warning,
  generating_points: styles.warning,
  writing_resume: styles.warning,
  rendering_latex: styles.warning,
  completed: styles.success,
  failed: styles.error,
};

const ACTIVE_STATUSES = new Set([
  'matching',
  'generating_points',
  'writing_resume',
  'rendering_latex',
]);

const StatusBadge = ({ status }: StatusBadgeProps) => {
  const label = STATUS_LABELS[status] ?? status;
  const styleClass = STATUS_STYLE[status] ?? styles.info;
  const isActive = ACTIVE_STATUSES.has(status);

  return (
    <span
      className={`${styles.badge} ${styleClass} ${isActive ? styles.pulse : ''}`}
    >
      {isActive && <span className={styles.dot} />}
      {label}
    </span>
  );
};

export default StatusBadge;
