import styles from './LoadingSpinner.module.css';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
}

const SIZE_CLASS: Record<string, string> = {
  sm: styles.sm,
  md: styles.md,
  lg: styles.lg,
};

const LoadingSpinner = ({ message, size = 'md' }: LoadingSpinnerProps) => {
  const sizeClass = SIZE_CLASS[size] ?? styles.md;

  return (
    <div className={styles.container}>
      <div className={`${styles.spinner} ${sizeClass}`} />
      {message && <p className={styles.message}>{message}</p>}
    </div>
  );
};

export default LoadingSpinner;
