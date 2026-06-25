/**
 * TypeScript interfaces mirroring backend/app/models/profile.py
 */

export interface Link {
  linkedin?: string;
  github?: string;
  portfolio?: string;
  website?: string;
}

export interface Education {
  school: string;
  degree: string;
  start_date: string;
  end_date: string;
  location: string;
  gpa?: string;
  coursework: string[];
}

export interface Experience {
  company: string;
  role: string;
  start_date: string;
  end_date: string;
  location: string;
  description: string;
  highlights: string[];
}

export interface PersonalProject {
  name: string;
  tech_stack: string[];
  description: string;
  url?: string;
}

export interface Publication {
  title: string;
  authors: string;
  venue: string;
  year: string;
  url?: string;
  description?: string;
}

export interface SkillSet {
  languages: string[];
  frameworks: string[];
  tools: string[];
  domains: string[];
}

export interface Certificate {
  name: string;
  issuer: string;
  date?: string;
  url?: string;
}

export interface Leadership {
  organization: string;
  role: string;
  start_date: string;
  end_date: string;
  description: string;
}

export interface CustomSection {
  title: string;
  items: string[];
}

export interface UserProfile {
  name: string;
  email: string;
  phone: string;
  location: string;
  links: Link;
  education: Education[];
  experience: Experience[];
  personal_projects: PersonalProject[];
  publications: Publication[];
  skills: SkillSet;
  certifications: Certificate[];
  leadership: Leadership[];
  custom_sections: CustomSection[];
  section_order: string[];
  subjective_profile_path: string;
  subjective_profile_content: string;
}
