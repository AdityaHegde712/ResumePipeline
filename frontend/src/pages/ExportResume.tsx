import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApplication } from '../api/history';
import { downloadLatex, downloadPdf, getPdfAvailable } from '../api/resume';
import LoadingSpinner from '../components/common/LoadingSpinner';
import EmptyState from '../components/common/EmptyState';
import ErrorState from '../components/common/ErrorState';
import StatusBadge from '../components/common/StatusBadge';
import { formatDate } from '../utils/dates';
import styles from './ExportResume.module.css';

export default function ExportResume() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: app, isLoading, isError, error, refetch } = useApplication(id);

  const [latex, setLatex] = useState('');
  const [latexLoading, setLatexLoading] = useState(true);
  const [latexError, setLatexError] = useState('');
  const [pdfAvailable, setPdfAvailable] = useState<boolean | null>(null);
  const [copied, setCopied] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState('');

  useEffect(() => {
    if (!id) return;
    setLatexLoading(true);
    setLatexError('');
    downloadLatex(id)
      .then((tex) => { setLatex(tex); setLatexLoading(false); })
      .catch((err) => { setLatexError((err as Error).message); setLatexLoading(false); });
    getPdfAvailable().then(setPdfAvailable).catch(() => setPdfAvailable(false));
  }, [id]);

  const handleDownloadTex = async () => {
    if (!id || !latex) return;
    try {
      const content = await downloadLatex(id);
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resume-${app?.company_name ?? 'export'}-${app?.job_title ?? 'resume'}.tex`.replace(/[^a-zA-Z0-9._-]/g, '_');
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setLatexError((err as Error).message);
    }
  };

  const handleDownloadPdf = async () => {
    if (!id) return;
    setPdfLoading(true);
    setPdfError('');
    try {
      const blob = await downloadPdf(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resume-${app?.company_name ?? 'export'}-${app?.job_title ?? 'resume'}.pdf`.replace(/[^a-zA-Z0-9._-]/g, '_');
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setPdfError((err as Error).message);
    } finally {
      setPdfLoading(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(latex);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available
    }
  };

  if (isLoading) return <LoadingSpinner message="Loading application..." />;
  if (isError) return <ErrorState message={(error as Error)?.message || 'Failed to load'} onRetry={() => refetch()} />;
  if (!app) return <ErrorState message="Application not found" />;
  if (!app.generated) return <EmptyState title="Resume not generated yet" description="Complete the generation process first" actionLabel="Back to Review" onAction={() => navigate(`/review/${id}`)} />;

  const totalBullets = app.generated.resume_points.reduce((sum, sec) => sum + sec.bullets.length, 0);

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerInfo}>
          <h1>{app.company_name} — {app.job_title}</h1>
          <p>Resume export</p>
        </div>
        <div className={styles.navLinks}>
          <button className={styles.navLink} onClick={() => navigate(`/review/${id}`)}>← Back to Review</button>
          <button className={styles.navLink} onClick={() => navigate('/new')}>New Application</button>
        </div>
      </div>

      {/* LaTeX Preview */}
      {latexLoading ? (
        <LoadingSpinner message="Preparing LaTeX..." />
      ) : latexError ? (
        <ErrorState message={latexError} onRetry={() => {
          if (!id) return;
          setLatexLoading(true);
          setLatexError('');
          downloadLatex(id).then((tex) => { setLatex(tex); setLatexLoading(false); }).catch((err) => { setLatexError((err as Error).message); setLatexLoading(false); });
        }} />
      ) : (
        <pre className={styles.codeBlock}><code>{latex}</code></pre>
      )}

      {/* Actions */}
      <div className={styles.actions}>
        <button className={`${styles.actionBtn} ${styles.primary}`} onClick={handleDownloadTex} disabled={!latex}>
          ⬇ Download .tex
        </button>
        <button
          className={styles.actionBtn}
          onClick={handleDownloadPdf}
          disabled={!pdfAvailable || pdfLoading}
          title={pdfAvailable === false ? 'PDF compiler not available — install MiKTeX' : ''}
        >
          {pdfLoading ? 'Generating PDF...' : '⬇ Download PDF'}
        </button>
        <button className={styles.actionBtn} onClick={handleCopy} disabled={!latex}>
          {copied ? <span className={styles.copied}>✓ Copied!</span> : '📋 Copy LaTeX'}
        </button>
        <button className={styles.actionBtn} onClick={() => window.open('https://www.overleaf.com', '_blank')}>
          🌐 Open in Overleaf
        </button>
      </div>

      {pdfError && <p style={{ color: 'var(--error)', fontSize: '0.8rem', marginBottom: '1rem' }}>{pdfError}</p>}

      {/* Info Bar */}
      <div className={styles.infoBar}>
        <div className={styles.infoItem}>
          <span className={styles.infoLabel}>Model</span>
          <span className={styles.infoValue}>{app.generated.model_used}</span>
        </div>
        <div className={styles.infoItem}>
          <span className={styles.infoLabel}>Created</span>
          <span className={styles.infoValue}>{formatDate(app.created_at)}</span>
        </div>
        <div className={styles.infoItem}>
          <span className={styles.infoLabel}>Sections</span>
          <span className={styles.infoValue}>{app.generated.resume_points.length}</span>
        </div>
        <div className={styles.infoItem}>
          <span className={styles.infoLabel}>Bullets</span>
          <span className={styles.infoValue}>{totalBullets}</span>
        </div>
        <div className={styles.infoItem}>
          <span className={styles.infoLabel}>Status</span>
          <StatusBadge status={app.generation_status} />
        </div>
      </div>
    </div>
  );
}
