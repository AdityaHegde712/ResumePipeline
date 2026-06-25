/**
 * TypeScript interfaces mirroring backend/app/models/generation.py
 */

export interface TaskModelConfig {
  provider: string;
  model: string;
}

export interface LLMConfig {
  default_provider: string;
  default_model: string;
  tasks: Record<string, TaskModelConfig>;
}

export interface GenerationRequest {
  application_id: string;
  job_title: string;
  company_name: string;
  company_description?: string;
  job_description: string;
  selected_project_ids: string[];
  tone: string;
}

export interface MatchRequest {
  job_title: string;
  company_name: string;
  job_description: string;
}

export interface MatchResult {
  project_id: string;
  project_name: string;
  relevance_score: number;
  reasoning: string;
}

export interface PointsRegenerateRequest {
  application_id: string;
  section_key: string;
  custom_instructions?: string;
}

export interface ResumeExportRequest {
  application_id: string;
}

export interface SSEEvent {
  event: 'stage' | 'token' | 'section_complete' | 'error' | 'complete';
  data: Record<string, unknown>;
}
