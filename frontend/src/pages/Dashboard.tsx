import { useNavigate } from 'react-router-dom';
import { useApplications } from '../api/history';
import { useProjects } from '../api/projects';
import LoadingSpinner from '../components/common/LoadingSpinner';
import EmptyState from '../components/common/EmptyState';
import ErrorState from '../components/common/ErrorState';
import StatusBadge from '../components/common/StatusBadge';
import { formatDate } from '../utils/dates';
import styles from './Dashboard.module.css';

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: apps, isLoading: appsLoading, isError: appsError, error: appsErr, refetch: refetchApps } = useApplications();
  const { data: projects, isLoading: projectsLoading } = useProjects();

  if (appsLoading || projectsLoading) return <LoadingSpinner message="Loading dashboard..." />;

  const stats = {
    total: apps?.length ?? 0,
    completed: apps?.filter((a) => a.generation_status === 'completed')?.length ?? 0,
    projects: projects?.length ?? 0,
  };

  const recentApps = apps
    ? [...apps].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5)
    : [];

  return (
    <div className={styles.container}>
      <h1 className={styles.pageTitle}>Dashboard</h1>

      {/* Stats */}
      <div className={styles.statsRow}>
        <div className={styles.statCard}>
          <span className={styles.statNumber}>{stats.total}</span>
          <span className={styles.statLabel}>Total Applications</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statNumber}>{stats.completed}</span>
          <span className={styles.statLabel}>Completed Resumes</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statNumber}>{stats.projects}</span>
          <span className={styles.statLabel}>Projects Available</span>
        </div>
      </div>

      {/* Quick Actions */}
      <div className={styles.quickActions}>
        <div className={styles.actionCard} onClick={() => navigate('/new')} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && navigate('/new')}>
          <span className={styles.actionIcon}>➕</span>
          <span className={styles.actionTitle}>New Application</span>
          <span className={styles.actionDesc}>Create a new resume tailored to a job</span>
        </div>
        <div className={styles.actionCard} onClick={() => navigate('/profile')} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && navigate('/profile')}>
          <span className={styles.actionIcon}>👤</span>
          <span className={styles.actionTitle}>View Profile</span>
          <span className={styles.actionDesc}>Update your personal information and skills</span>
        </div>
        <div className={styles.actionCard} onClick={() => navigate('/new')} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && navigate('/new')}>
          <span className={styles.actionIcon}>📂</span>
          <span className={styles.actionTitle}>Browse Projects</span>
          <span className={styles.actionDesc}>Review your project portfolio for matching</span>
        </div>
      </div>

      {/* Recent Applications */}
      <div className={styles.recentSection}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Recent Applications</h2>
          {apps && apps.length > 0 && (
            <button className={styles.viewAll} onClick={() => navigate('/history')}>View all</button>
          )}
        </div>

        {appsError ? (
          <ErrorState message={(appsErr as Error)?.message || 'Failed to load applications'} onRetry={() => refetchApps()} />
        ) : recentApps.length === 0 ? (
          <EmptyState title="No applications yet" description="Create your first application to get started" actionLabel="New Application" onAction={() => navigate('/new')} />
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Company</th>
                <th>Job Title</th>
                <th>Status</th>
                <th>Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {recentApps.map((app) => (
                <tr key={app.id}>
                  <td>{app.company_name}</td>
                  <td>{app.job_title}</td>
                  <td><StatusBadge status={app.generation_status} /></td>
                  <td>{formatDate(app.created_at)}</td>
                  <td>
                    <button className={styles.viewBtn} onClick={() => navigate(`/review/${app.id}`)}>View</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
