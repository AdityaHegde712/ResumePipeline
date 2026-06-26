import { useState, type FormEvent } from 'react';
import styles from './ApplicationForm.module.css';

interface ApplicationFormData {
  application_id: string;
  job_title: string;
  company_name: string;
  company_description?: string;
  job_description: string;
  selected_project_ids: string[];
  tone: string;
}

interface ApplicationFormProps {
  onSubmit: (data: ApplicationFormData) => void;
  loading?: boolean;
}

export default function ApplicationForm({ onSubmit, loading }: ApplicationFormProps) {
  const [jobTitle, setJobTitle] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [companyDesc, setCompanyDesc] = useState('');
  const [jobDesc, setJobDesc] = useState('');
  const [tone, setTone] = useState('professional');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (!jobTitle.trim()) errs.jobTitle = 'Job title is required';
    if (!companyName.trim()) errs.companyName = 'Company name is required';
    if (!jobDesc.trim()) errs.jobDesc = 'Job description is required';
    else if (jobDesc.trim().length < 50) errs.jobDesc = 'Job description must be at least 50 characters';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    onSubmit({
      application_id: '',
      job_title: jobTitle.trim(),
      company_name: companyName.trim(),
      company_description: companyDesc.trim() || undefined,
      job_description: jobDesc.trim(),
      selected_project_ids: [],
      tone,
    });
  };

  const descLength = jobDesc.trim().length;
  const charClass = descLength === 0 ? '' : descLength < 50 ? styles.error : styles.warning;

  return (
    <form className={styles.formCard} onSubmit={handleSubmit}>
      <div className={styles.field}>
        <label className={styles.label}>Job Title *</label>
        <input
          className={styles.input}
          type="text"
          value={jobTitle}
          onChange={(e) => setJobTitle(e.target.value)}
          placeholder="e.g., Software Engineer Intern"
        />
        {errors.jobTitle && <span className={styles.fieldError}>{errors.jobTitle}</span>}
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Company Name *</label>
        <input
          className={styles.input}
          type="text"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          placeholder="e.g., Google"
        />
        {errors.companyName && <span className={styles.fieldError}>{errors.companyName}</span>}
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Company Description</label>
        <input
          className={styles.input}
          type="text"
          value={companyDesc}
          onChange={(e) => setCompanyDesc(e.target.value)}
          placeholder="Brief description of the company (optional)"
        />
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Job Description *</label>
        <textarea
          className={styles.textarea}
          value={jobDesc}
          onChange={(e) => setJobDesc(e.target.value)}
          placeholder="Paste the full job description here (minimum 50 characters)..."
          rows={8}
        />
        <span className={`${styles.charCount} ${charClass}`}>
          {descLength} / 50 min
        </span>
        {errors.jobDesc && <span className={styles.fieldError}>{errors.jobDesc}</span>}
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Tone</label>
        <select className={styles.select} value={tone} onChange={(e) => setTone(e.target.value)}>
          <option value="professional">Professional</option>
          <option value="technical">Technical</option>
          <option value="concise">Concise</option>
          <option value="detailed">Detailed</option>
        </select>
      </div>

      <button className={styles.submitBtn} type="submit" disabled={loading}>
        {loading ? 'Generating...' : 'Generate Resume Points'}
      </button>
    </form>
  );
}
