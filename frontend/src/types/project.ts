/**
 * TypeScript interfaces mirroring backend/app/models/project.py
 */

export interface ProjectEntry {
  id: string;
  name: string;
  type: string;
  summary: string;
  tech_stack: string[];
  key_features: string[];
  resume_value_bullets: string[];
  domains: string[];
  lines_of_code?: number;
  source_section: string;
}
