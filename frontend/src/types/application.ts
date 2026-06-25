/**
 * TypeScript interfaces mirroring backend/app/models/application.py
 */

export enum GenerationStatus {
  PENDING = 'pending',
  MATCHING = 'matching',
  GENERATING_POINTS = 'generating_points',
  WRITING_RESUME = 'writing_resume',
  RENDERING_LATEX = 'rendering_latex',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface BulletPoint {
  id: string;
  section: string;
  text: string;
  order: number;
  edited: boolean;
}

export interface SectionPoints {
  section_key: string;
  section_title: string;
  bullets: BulletPoint[];
}

export interface GeneratedContent {
  resume_points: SectionPoints[];
  resume_latex?: string;
  model_used: string;
}

export interface Application {
  id: string;
  created_at: string;
  updated_at: string;
  company_name: string;
  company_description?: string;
  job_title: string;
  job_description: string;
  selected_project_ids: string[];
  generation_status: GenerationStatus;
  generated?: GeneratedContent;
  error_message?: string;
}
