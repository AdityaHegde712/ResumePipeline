import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { streamGeneratePoints } from '../api/resume';
import ApplicationForm from '../components/forms/ApplicationForm';
import ErrorState from '../components/common/ErrorState';
import ProgressPanel from '../components/generation/ProgressPanel';
import type { GenerationRequest } from '../types';
import styles from './NewApplication.module.css';

type PageState = 'idle' | 'generating' | 'error';

const STAGES = ['matching', 'generating_points', 'writing_resume', 'rendering_latex'];

export default function NewApplication() {
  const navigate = useNavigate();

  const [pageState, setPageState] = useState<PageState>('idle');
  const [genStage, setGenStage] = useState('');
  const [genMessage, setGenMessage] = useState('');
  const [genTokens, setGenTokens] = useState('');
  const [genError, setGenError] = useState('');

  const handleGenerate = async (data: GenerationRequest) => {
    setPageState('generating');
    setGenTokens('');
    setGenError('');

    await streamGeneratePoints(
      { ...data, selected_project_ids: [] },
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
    </div>
  );
}
