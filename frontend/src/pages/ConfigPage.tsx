import { useState, useEffect } from 'react';
import { useLLMConfig, useUpdateLLMConfig } from '../api/history';
import { useProjects, useRefreshProjects } from '../api/projects';
import { getPdfAvailable } from '../api/resume';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorState from '../components/common/ErrorState';
import type { LLMConfig } from '../types';
import styles from './ConfigPage.module.css';

export default function ConfigPage() {
  const { data: config, isLoading: configLoading, isError: configError, error: configErr, refetch: refetchConfig } = useLLMConfig();
  const updateConfig = useUpdateLLMConfig();
  const { data: projects } = useProjects();
  const refreshProjects = useRefreshProjects();

  const [localConfig, setLocalConfig] = useState<LLMConfig | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [saveError, setSaveError] = useState('');
  const [pdfAvailable, setPdfAvailable] = useState<boolean | null>(null);
  const [newTaskKey, setNewTaskKey] = useState('');

  useEffect(() => {
    if (config) setLocalConfig(JSON.parse(JSON.stringify(config)));
  }, [config]);

  useEffect(() => {
    getPdfAvailable().then(setPdfAvailable).catch(() => setPdfAvailable(false));
  }, []);

  const handleSave = async () => {
    if (!localConfig) return;
    setSaveStatus('saving');
    try {
      await updateConfig.mutateAsync(localConfig);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (err) {
      setSaveStatus('error');
      setSaveError((err as Error).message);
    }
  };

  const addTask = () => {
    if (!localConfig || !newTaskKey.trim()) return;
    const key = newTaskKey.trim();
    if (key in localConfig.tasks) return;
    setLocalConfig({
      ...localConfig,
      tasks: { ...localConfig.tasks, [key]: { provider: '', model: '' } },
    });
    setNewTaskKey('');
  };

  const updateTask = (key: string, field: 'provider' | 'model', value: string) => {
    if (!localConfig) return;
    setLocalConfig({
      ...localConfig,
      tasks: {
        ...localConfig.tasks,
        [key]: { ...localConfig.tasks[key], [field]: value },
      },
    });
  };

  const removeTask = (key: string) => {
    if (!localConfig) return;
    const tasks = { ...localConfig.tasks };
    delete tasks[key];
    setLocalConfig({ ...localConfig, tasks });
  };

  if (configLoading) return <LoadingSpinner message="Loading configuration..." />;
  if (configError) return <ErrorState message={(configErr as Error)?.message || 'Failed to load config'} onRetry={() => refetchConfig()} />;
  if (!localConfig) return null;

  return (
    <div className={styles.container}>
      <h1 className={styles.pageTitle}>Settings</h1>

      {/* LLM Config */}
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>LLM Configuration</h2>
        <div className={styles.fieldRow}>
          <label className={styles.fieldLabel}>Default Provider</label>
          <input className={styles.fieldInput} value={localConfig.default_provider} onChange={(e) => setLocalConfig({ ...localConfig, default_provider: e.target.value })} />
        </div>
        <div className={styles.fieldRow}>
          <label className={styles.fieldLabel}>Default Model</label>
          <input className={styles.fieldInput} value={localConfig.default_model} onChange={(e) => setLocalConfig({ ...localConfig, default_model: e.target.value })} />
        </div>

        <h3 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: '1.5rem 0 0.75rem' }}>Task-specific overrides</h3>
        {Object.entries(localConfig.tasks).map(([key, task]) => (
          <div key={key} className={styles.taskRow}>
            <input className={styles.taskInput} value={key} disabled style={{ opacity: 0.6 }} />
            <input className={styles.taskInput} placeholder="Provider" value={task.provider} onChange={(e) => updateTask(key, 'provider', e.target.value)} />
            <input className={styles.taskInput} placeholder="Model" value={task.model} onChange={(e) => updateTask(key, 'model', e.target.value)} />
            <button className={styles.removeBtn} onClick={() => removeTask(key)}>✕</button>
          </div>
        ))}

        <div className={styles.taskRow}>
          <input className={styles.taskInput} placeholder="New task key..." value={newTaskKey} onChange={(e) => setNewTaskKey(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addTask()} />
          <button className={styles.addBtn} style={{ width: 'auto' }} onClick={addTask}>+ Add</button>
        </div>

        <button className={styles.saveBtn} onClick={handleSave} disabled={saveStatus === 'saving'}>
          {saveStatus === 'saving' ? 'Saving...' : 'Save Configuration'}
        </button>
        {saveStatus === 'saved' && <div className={styles.successMsg}>Configuration saved ✓</div>}
        {saveStatus === 'error' && <div className={styles.errorMsg}>Error: {saveError}</div>}
      </div>

      {/* PDF Compiler */}
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>PDF Compiler Status</h2>
        <div className={styles.statusRow}>
          <span>PDF Compiler:</span>
          {pdfAvailable === null ? (
            <LoadingSpinner size="sm" />
          ) : pdfAvailable ? (
            <span className={styles.statusAvailable}>Available ✅</span>
          ) : (
            <span className={styles.statusUnavailable}>Not available ❌</span>
          )}
          <button className={styles.checkBtn} onClick={() => { setPdfAvailable(null); getPdfAvailable().then(setPdfAvailable).catch(() => setPdfAvailable(false)); }}>
            Check Again
          </button>
        </div>
      </div>

      {/* Sweep File */}
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>Projects Data</h2>
        <div className={styles.projectsCount}>Projects available: <strong>{projects?.length ?? 0}</strong></div>
        <button className={styles.refreshBtn} onClick={() => refreshProjects.mutate()} disabled={refreshProjects.isPending}>
          {refreshProjects.isPending ? 'Refreshing...' : 'Refresh Sweep File'}
        </button>
      </div>
    </div>
  );
}
