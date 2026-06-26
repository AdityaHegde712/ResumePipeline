import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApplications, useDeleteApplication } from '../api/history';
import LoadingSpinner from '../components/common/LoadingSpinner';
import EmptyState from '../components/common/EmptyState';
import ErrorState from '../components/common/ErrorState';
import ConfirmDialog from '../components/common/ConfirmDialog';
import StatusBadge from '../components/common/StatusBadge';
import { formatDate } from '../utils/dates';
import styles from './HistoryPage.module.css';

export default function HistoryPage() {
  const navigate = useNavigate();
  const { data: apps, isLoading, isError, error, refetch } = useApplications();
  const deleteApp = useDeleteApplication();

  const [search, setSearch] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  const filtered = useMemo(() => {
    if (!apps) return [];
    const q = search.toLowerCase();
    return [...apps]
      .filter((a) => !q || a.company_name.toLowerCase().includes(q) || a.job_title.toLowerCase().includes(q))
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [apps, search]);

  if (isLoading) return <LoadingSpinner message="Loading applications..." />;
  if (isError) return <ErrorState message={(error as Error)?.message || 'Failed to load'} onRetry={() => refetch()} />;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.headerTitle}>Application History</h1>
        <button className="btn btn-primary" onClick={() => navigate('/new')}>+ New Application</button>
      </div>

      {apps && apps.length > 0 && (
        <input
          className={styles.searchInput}
          type="text"
          placeholder="Search by company or job title..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      )}

      {filtered.length === 0 ? (
        <EmptyState
          title={apps?.length ? 'No matches' : 'No applications yet'}
          description={apps?.length ? 'Try a different search term' : 'Create your first application to get started'}
          actionLabel={apps?.length ? undefined : 'Create Application'}
          onAction={apps?.length ? undefined : () => navigate('/new')}
        />
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Company</th>
              <th>Job Title</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((app) => (
              <tr key={app.id}>
                <td>{app.company_name}</td>
                <td>{app.job_title}</td>
                <td><StatusBadge status={app.generation_status} /></td>
                <td>{formatDate(app.created_at)}</td>
                <td>
                  <div className={styles.actionsCell}>
                    <button className={styles.actionBtn} onClick={() => navigate(`/review/${app.id}`)}>View</button>
                    <button className={styles.actionBtn} onClick={() => navigate(`/export/${app.id}`)}>Export</button>
                    <button className={`${styles.actionBtn} ${styles.danger}`} onClick={() => setDeleteTarget({ id: app.id, name: `${app.company_name} - ${app.job_title}` })}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {deleteTarget && (
        <ConfirmDialog
          open
          title="Delete Application"
          message={`Are you sure you want to delete the application for ${deleteTarget.name}?`}
          confirmLabel="Delete"
          variant="danger"
          onConfirm={() => {
            deleteApp.mutate(deleteTarget.id);
            setDeleteTarget(null);
          }}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
