import { apiClient } from './client';
import type { GenerationRequest, PointsRegenerateRequest, SSEEvent } from '../types';

function parseSSELine(line: string): SSEEvent | null {
  if (!line || !line.startsWith('data: ')) return null;
  const jsonStr = line.slice(6).trim();
  if (!jsonStr || jsonStr === '[DONE]') return null;
  try {
    return JSON.parse(jsonStr) as SSEEvent;
  } catch {
    return null;
  }
}

interface StreamCallbacks {
  onStage?: (stage: string, message: string) => void;
  onToken?: (text: string) => void;
  onSectionComplete?: (section: string, index: number, total: number) => void;
  onError?: (error: string) => void;
  onComplete?: (result: unknown) => void;
}

async function streamEvent(
  endpoint: string,
  body: unknown,
  callbacks: StreamCallbacks
): Promise<void> {
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const response = await fetch(
    `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api${endpoint}`,
    {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    }
  );

  if (!response.ok) {
    const text = await response.text();
    callbacks.onError?.(text || `HTTP ${response.status}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError?.('No response body');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const event = parseSSELine(line);
      if (!event) continue;

      switch (event.event) {
        case 'stage':
          callbacks.onStage?.(event.data.stage as string, event.data.message as string);
          break;
        case 'token':
          callbacks.onToken?.(event.data.text as string);
          break;
        case 'section_complete':
          callbacks.onSectionComplete?.(
            event.data.section as string,
            event.data.index as number,
            event.data.total as number
          );
          break;
        case 'error':
          callbacks.onError?.(event.data.message as string);
          break;
        case 'complete':
          callbacks.onComplete?.(event.data);
          break;
      }
    }
  }
}

export function streamGeneratePoints(
  req: GenerationRequest,
  callbacks: StreamCallbacks
): Promise<void> {
  return streamEvent('/generate/points', req, callbacks);
}

export function streamGenerateResume(
  appId: string,
  callbacks: StreamCallbacks
): Promise<void> {
  return streamEvent(`/generate/resume`, { application_id: appId }, callbacks);
}

export function streamRegenerateSection(
  req: PointsRegenerateRequest,
  callbacks: StreamCallbacks
): Promise<void> {
  return streamEvent('/generate/regenerate-section', req, callbacks);
}

export async function downloadLatex(applicationId: string): Promise<string> {
  const { data } = await apiClient.get(`/resume/${applicationId}/tex`);
  return data.tex as string;
}

export async function downloadPdf(applicationId: string): Promise<Blob> {
  const { data } = await apiClient.get(`/resume/${applicationId}/pdf`, {
    responseType: 'blob',
  });
  return data as Blob;
}

export async function getPdfAvailable(): Promise<boolean> {
  const { data } = await apiClient.get('/config/pdf-available');
  return data.available as boolean;
}
