import { useState } from 'react';
import type { UserProfile, Education, Experience, Publication, Certificate, Leadership } from '../../types';
import TagInput from '../common/TagInput';
import styles from './ProfileForm.module.css';

interface ProfileFormProps {
  profile: UserProfile;
  onChange: (profile: UserProfile) => void;
}

const EMPTY_EDUCATION = (): Education => ({ school: '', degree: '', start_date: '', end_date: '', location: '', coursework: [] });
const EMPTY_EXPERIENCE = (): Experience => ({ company: '', role: '', start_date: '', end_date: '', location: '', description: '', highlights: [] });

const EMPTY_PUBLICATION = (): Publication => ({ title: '', authors: '', venue: '', year: '' });
const EMPTY_CERTIFICATE = (): Certificate => ({ name: '', issuer: '' });
const EMPTY_LEADERSHIP = (): Leadership => ({ organization: '', role: '', start_date: '', end_date: '', description: '' });

type SectionKey = 'personal' | 'links' | 'education' | 'experience' | 'projects' | 'publications' | 'certifications' | 'leadership' | 'section_order';

const ALL_SECTIONS: { key: SectionKey; label: string }[] = [
  { key: 'personal', label: 'Personal Info' },
  { key: 'links', label: 'Links' },
  { key: 'education', label: 'Education' },
  { key: 'experience', label: 'Experience' },

  { key: 'publications', label: 'Publications' },

  { key: 'certifications', label: 'Certifications' },
  { key: 'leadership', label: 'Leadership' },
  { key: 'section_order', label: 'Section Order' },
];

export default function ProfileForm({ profile, onChange }: ProfileFormProps) {
  const [openSections, setOpenSections] = useState<Set<SectionKey>>(new Set(['personal']));

  const toggleSection = (key: SectionKey) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const updateSimple = <K extends keyof UserProfile>(key: K, value: UserProfile[K]) => {
    onChange({ ...profile, [key]: value });
  };

  const updateArrayItem = <TItem,>(items: TItem[], index: number, updates: Partial<TItem>) => {
    const next = [...items];
    next[index] = { ...next[index], ...updates } as TItem;
    return next;
  };

  return (
    <div className={styles.container}>
      {ALL_SECTIONS.map(({ key, label }) => {
        const isOpen = openSections.has(key);
        return (
          <div key={key} className={`${styles.section} ${isOpen ? styles.open : ''}`}>
            <button className={styles.sectionHeader} onClick={() => toggleSection(key)} type="button">
              <span className={styles.sectionLabel}>{label}</span>
              <span className={styles.chevron}>{isOpen ? '▼' : '▶'}</span>
            </button>
            {isOpen && (
              <div className={styles.sectionContent}>
                {key === 'personal' && (
                  <div className={styles.grid2}>
                    <input className={styles.input} placeholder="Name" value={profile.name} onChange={(e) => updateSimple('name', e.target.value)} />
                    <input className={styles.input} placeholder="Email" value={profile.email} onChange={(e) => updateSimple('email', e.target.value)} />
                    <input className={styles.input} placeholder="Phone" value={profile.phone} onChange={(e) => updateSimple('phone', e.target.value)} />
                    <input className={styles.input} placeholder="Location" value={profile.location} onChange={(e) => updateSimple('location', e.target.value)} />
                  </div>
                )}
                {key === 'links' && (
                  <div className={styles.grid2}>
                    <input className={styles.input} placeholder="LinkedIn URL" value={profile.links.linkedin || ''} onChange={(e) => onChange({ ...profile, links: { ...profile.links, linkedin: e.target.value } })} />
                    <input className={styles.input} placeholder="GitHub URL" value={profile.links.github || ''} onChange={(e) => onChange({ ...profile, links: { ...profile.links, github: e.target.value } })} />
                    <input className={styles.input} placeholder="Portfolio URL" value={profile.links.portfolio || ''} onChange={(e) => onChange({ ...profile, links: { ...profile.links, portfolio: e.target.value } })} />
                    <input className={styles.input} placeholder="Website URL" value={profile.links.website || ''} onChange={(e) => onChange({ ...profile, links: { ...profile.links, website: e.target.value } })} />
                  </div>
                )}
                {key === 'education' && (
                  <div>
                    {profile.education.map((edu, i) => (
                      <div key={i} className={styles.entryCard}>
                        <div className={styles.entryHeader}>
                          <span>{edu.school || `Education #${i + 1}`}</span>
                          <button type="button" className={styles.removeBtn} onClick={() => onChange({ ...profile, education: profile.education.filter((_, j) => j !== i) })}>✕</button>
                        </div>
                        <div className={styles.grid2}>
                          <input className={styles.input} placeholder="School" value={edu.school} onChange={(e) => onChange({ ...profile, education: updateArrayItem(profile.education, i, { school: e.target.value }) })} />
                          <input className={styles.input} placeholder="Degree" value={edu.degree} onChange={(e) => onChange({ ...profile, education: updateArrayItem(profile.education, i, { degree: e.target.value }) })} />
                          <input className={styles.input} type="date" value={edu.start_date} onChange={(e) => onChange({ ...profile, education: updateArrayItem(profile.education, i, { start_date: e.target.value }) })} />
                          <input className={styles.input} type="date" value={edu.end_date} onChange={(e) => onChange({ ...profile, education: updateArrayItem(profile.education, i, { end_date: e.target.value }) })} />
                          <input className={styles.input} placeholder="Location" value={edu.location} onChange={(e) => onChange({ ...profile, education: updateArrayItem(profile.education, i, { location: e.target.value }) })} />
                          <input className={styles.input} placeholder="GPA (optional)" value={edu.gpa || ''} onChange={(e) => onChange({ ...profile, education: updateArrayItem(profile.education, i, { gpa: e.target.value }) })} />
                        </div>
                        <TagInput tags={edu.coursework} onChange={(tags) => onChange({ ...profile, education: updateArrayItem(profile.education, i, { coursework: tags }) })} placeholder="Add course..." label="Coursework" />
                      </div>
                    ))}
                    <button type="button" className={styles.addBtn} onClick={() => onChange({ ...profile, education: [...profile.education, EMPTY_EDUCATION()] })}>+ Add Education</button>
                  </div>
                )}
                {key === 'experience' && (
                  <div>
                    {profile.experience.map((exp, i) => (
                      <div key={i} className={styles.entryCard}>
                        <div className={styles.entryHeader}>
                          <span>{exp.company || `Experience #${i + 1}`}</span>
                          <button type="button" className={styles.removeBtn} onClick={() => onChange({ ...profile, experience: profile.experience.filter((_, j) => j !== i) })}>✕</button>
                        </div>
                        <div className={styles.grid2}>
                          <input className={styles.input} placeholder="Company" value={exp.company} onChange={(e) => onChange({ ...profile, experience: updateArrayItem(profile.experience, i, { company: e.target.value }) })} />
                          <input className={styles.input} placeholder="Role" value={exp.role} onChange={(e) => onChange({ ...profile, experience: updateArrayItem(profile.experience, i, { role: e.target.value }) })} />
                          <input className={styles.input} type="date" value={exp.start_date} onChange={(e) => onChange({ ...profile, experience: updateArrayItem(profile.experience, i, { start_date: e.target.value }) })} />
                          <input className={styles.input} type="date" value={exp.end_date} onChange={(e) => onChange({ ...profile, experience: updateArrayItem(profile.experience, i, { end_date: e.target.value }) })} />
                          <input className={styles.input} placeholder="Location" value={exp.location} onChange={(e) => onChange({ ...profile, experience: updateArrayItem(profile.experience, i, { location: e.target.value }) })} />
                        </div>
                        <textarea className={styles.textarea} placeholder="Description" value={exp.description} onChange={(e) => onChange({ ...profile, experience: updateArrayItem(profile.experience, i, { description: e.target.value }) })} rows={3} />
                        <TagInput tags={exp.highlights} onChange={(tags) => onChange({ ...profile, experience: updateArrayItem(profile.experience, i, { highlights: tags }) })} placeholder="Add highlight..." label="Highlights" />
                      </div>
                    ))}
                    <button type="button" className={styles.addBtn} onClick={() => onChange({ ...profile, experience: [...profile.experience, EMPTY_EXPERIENCE()] })}>+ Add Experience</button>
                  </div>
                )}

                {key === 'publications' && (
                  <div>
                    {profile.publications.map((pub, i) => (
                      <div key={i} className={styles.entryCard}>
                        <div className={styles.entryHeader}>
                          <span>{`Publication #${i + 1}`}</span>
                          <button type="button" className={styles.removeBtn} onClick={() => onChange({ ...profile, publications: profile.publications.filter((_, j) => j !== i) })}>✕</button>
                        </div>
                        <textarea className={styles.textarea} placeholder="Full citation (e.g. LastName et al., Title, Venue, Year)" value={pub.title} onChange={(e) => onChange({ ...profile, publications: updateArrayItem(profile.publications, i, { title: e.target.value }) })} rows={2} />
                      </div>
                    ))}
                    <button type="button" className={styles.addBtn} onClick={() => onChange({ ...profile, publications: [...profile.publications, EMPTY_PUBLICATION()] })}>+ Add Publication</button>
                  </div>
                )}

                {key === 'certifications' && (
                  <div>
                    {profile.certifications.map((cert, i) => (
                      <div key={i} className={styles.entryCard}>
                        <div className={styles.entryHeader}>
                          <span>{cert.name || `Certification #${i + 1}`}</span>
                          <button type="button" className={styles.removeBtn} onClick={() => onChange({ ...profile, certifications: profile.certifications.filter((_, j) => j !== i) })}>✕</button>
                        </div>
                        <div className={styles.grid2}>
                          <input className={styles.input} placeholder="Name" value={cert.name} onChange={(e) => onChange({ ...profile, certifications: updateArrayItem(profile.certifications, i, { name: e.target.value }) })} />
                          <input className={styles.input} placeholder="Issuer" value={cert.issuer} onChange={(e) => onChange({ ...profile, certifications: updateArrayItem(profile.certifications, i, { issuer: e.target.value }) })} />
                          <input className={styles.input} placeholder="Date (optional)" value={cert.date || ''} onChange={(e) => onChange({ ...profile, certifications: updateArrayItem(profile.certifications, i, { date: e.target.value }) })} />
                          <input className={styles.input} placeholder="URL (optional)" value={cert.url || ''} onChange={(e) => onChange({ ...profile, certifications: updateArrayItem(profile.certifications, i, { url: e.target.value }) })} />
                        </div>
                      </div>
                    ))}
                    <button type="button" className={styles.addBtn} onClick={() => onChange({ ...profile, certifications: [...profile.certifications, EMPTY_CERTIFICATE()] })}>+ Add Certification</button>
                  </div>
                )}
                {key === 'leadership' && (
                  <div>
                    {profile.leadership.map((lead, i) => (
                      <div key={i} className={styles.entryCard}>
                        <div className={styles.entryHeader}>
                          <span>{lead.organization || `Leadership #${i + 1}`}</span>
                          <button type="button" className={styles.removeBtn} onClick={() => onChange({ ...profile, leadership: profile.leadership.filter((_, j) => j !== i) })}>✕</button>
                        </div>
                        <div className={styles.grid2}>
                          <input className={styles.input} placeholder="Organization" value={lead.organization} onChange={(e) => onChange({ ...profile, leadership: updateArrayItem(profile.leadership, i, { organization: e.target.value }) })} />
                          <input className={styles.input} placeholder="Role" value={lead.role} onChange={(e) => onChange({ ...profile, leadership: updateArrayItem(profile.leadership, i, { role: e.target.value }) })} />
                          <input className={styles.input} type="date" value={lead.start_date} onChange={(e) => onChange({ ...profile, leadership: updateArrayItem(profile.leadership, i, { start_date: e.target.value }) })} />
                          <input className={styles.input} type="date" value={lead.end_date} onChange={(e) => onChange({ ...profile, leadership: updateArrayItem(profile.leadership, i, { end_date: e.target.value }) })} />
                        </div>
                        <textarea className={styles.textarea} placeholder="Description" value={lead.description} onChange={(e) => onChange({ ...profile, leadership: updateArrayItem(profile.leadership, i, { description: e.target.value }) })} rows={2} />
                      </div>
                    ))}
                    <button type="button" className={styles.addBtn} onClick={() => onChange({ ...profile, leadership: [...profile.leadership, EMPTY_LEADERSHIP()] })}>+ Add Leadership</button>
                  </div>
                )}
                {key === 'section_order' && (
                  <div>
                    <p className={styles.hint}>Drag or use arrows to reorder resume sections</p>
                    {profile.section_order.map((sec, i) => (
                      <div key={sec} className={styles.orderItem}>
                        <span className={styles.orderIndex}>{i + 1}</span>
                        <span className={styles.orderLabel}>{sec.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</span>
                        <div className={styles.orderActions}>
                          <button type="button" className={styles.orderBtn} disabled={i === 0} onClick={() => {
                            const next = [...profile.section_order];
                            [next[i - 1], next[i]] = [next[i], next[i - 1]];
                            updateSimple('section_order', next);
                          }}>↑</button>
                          <button type="button" className={styles.orderBtn} disabled={i === profile.section_order.length - 1} onClick={() => {
                            const next = [...profile.section_order];
                            [next[i + 1], next[i]] = [next[i], next[i + 1]];
                            updateSimple('section_order', next);
                          }}>↓</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
