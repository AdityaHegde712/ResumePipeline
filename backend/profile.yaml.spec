{
  "name": "string (required) — full name shown at the top of the resume",
  "email": "string — email address shown in the resume header",
  "phone": "string — phone number shown in the resume header",
  "location": "string — city/state or region shown in the resume header",
  "links": {
    "linkedin": "string URL or null — LinkedIn profile link",
    "github": "string URL or null — GitHub profile link",
    "portfolio": "string URL or null — portfolio site link",
    "website": "string URL or null — personal website link"
  },
  "education": [
    {
      "school": "string (required) — institution name",
      "degree": "string (required) — degree earned or in progress",
      "start_date": "string (required) — e.g. 'Aug 2025'",
      "end_date": "string (required) — e.g. 'May 2027' or 'Present'",
      "location": "string (required) — campus city/state",
      "gpa": "string or null — e.g. '4.0'",
      "coursework": ["string — relevant course names"]
    }
  ],
  "experience": [
    {
      "company": "string (required) — employer name",
      "role": "string (required) — job title",
      "start_date": "string (required) — e.g. 'Jun 2024'",
      "end_date": "string (required) — e.g. 'Aug 2025' or 'Present'",
      "location": "string (required) — work location",
      "description": "string (required) — role overview paragraph",
      "highlights": ["string — bullet-point achievements"]
    }
  ],
  "personal_projects": [
    {
      "name": "string (required) — project name",
      "tech_stack": ["string — technologies used"],
      "description": "string (required) — project summary",
      "url": "string URL or null — project link"
    }
  ],
  "publications": [
    {
      "title": "string (required) — paper title",
      "authors": "string (required) — author list",
      "venue": "string (required) — conference/journal name",
      "year": "string (required) — publication year",
      "url": "string URL or null — DOI/link",
      "description": "string or null — optional one-line summary"
    }
  ],
  "skills": {
    "languages": ["string — programming languages"],
    "frameworks": ["string — frameworks/libraries"],
    "tools": ["string — developer tools"],
    "domains": ["string — expertise areas"]
  },
  "certifications": [
    {
      "name": "string (required) — certification name",
      "issuer": "string (required) — issuing body",
      "date": "string or null — e.g. '2025'",
      "url": "string URL or null — verification link"
    }
  ],
  "leadership": [
    {
      "organization": "string (required) — org/club name",
      "role": "string (required) — position held",
      "start_date": "string (required) — e.g. 'Sep 2023'",
      "end_date": "string (required) — e.g. 'May 2025' or 'Present'",
      "description": "string (required) — what you did"
    }
  ],
  "custom_sections": [
    {
      "title": "string (required) — custom section heading",
      "items": ["string — bullet lines for that section"]
    }
  ],
  "section_order": [
    "array of section keys in render order. Valid keys: 'education', 'skills', 'projects', 'experience', 'publications', 'leadership', 'certifications'. If omitted or empty, defaults to ['education', 'skills', 'projects', 'experience', 'publications', 'leadership', 'certifications']"
  ]
}
