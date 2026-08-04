// Typed fetch wrapper for the Resume Pipeline backend (PLAN §3, D10/D13, D16-D21).

export interface ApplicationResponse {
  status: number
  llm_generation: 'OK'
  reconstruction: 'OK'
  saved: 'OK'
  pdf_error: string | null
  application_id: string
  cover_letter: 'OK' | 'ERROR' | null
  cover_letter_generated: boolean
  cover_letter_error: string | null
}

export interface FatalPhaseError {
  phase: 'llm_generation' | 'reconstruction'
  error: string
}

export interface ApplicationRequestBody {
  job_position: string
  company_name: string
  company_description?: string | null
  job_description: string
  // Omitted when the user opts out; the backend defaults it to true.
  generate_cover_letter?: boolean
}

export interface CoverLetterResponse {
  cover_letter: 'OK' | 'ERROR'
  cover_letter_generated: boolean
  cover_letter_text?: string
  cover_letter_error?: string | null
}

export type DownloadKind = 'tex' | 'pdf'

export class ApplicationApiError extends Error {
  readonly phase: 'llm_generation' | 'reconstruction'

  constructor(phase: 'llm_generation' | 'reconstruction', message: string) {
    super(message)
    this.name = 'ApplicationApiError'
    this.phase = phase
  }
}

export class CoverLetterConflictError extends Error {
  constructor(message = 'Cover letter already generated') {
    super(message)
    this.name = 'CoverLetterConflictError'
  }
}

export async function createApplication(
  body: ApplicationRequestBody,
): Promise<ApplicationResponse> {
  const response = await fetch('/api/applications', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (response.status === 500) {
    const payload = (await response.json().catch(() => null)) as FatalPhaseError | null
    throw new ApplicationApiError(
      payload?.phase ?? 'reconstruction',
      payload?.error ?? 'Unknown server error',
    )
  }

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  return (await response.json()) as ApplicationResponse
}

export async function getLlmsResponse(applicationId: string): Promise<string> {
  const response = await fetch(
    `/api/applications/${encodeURIComponent(applicationId)}/llm_response`,
  )
  if (!response.ok) {
    throw new Error(`Failed to load LLM response (${response.status})`)
  }
  return response.text()
}

export async function generateCoverLetter(
  applicationId: string,
): Promise<CoverLetterResponse> {
  const response = await fetch(
    `/api/applications/${encodeURIComponent(applicationId)}/cover_letter`,
    { method: 'POST' },
  )

  if (response.status === 409) {
    throw new CoverLetterConflictError()
  }

  if (!response.ok) {
    throw new Error(`Failed to generate cover letter (${response.status})`)
  }

  return (await response.json()) as CoverLetterResponse
}

export async function getCoverLetterText(applicationId: string): Promise<string> {
  const response = await fetch(
    `/api/applications/${encodeURIComponent(applicationId)}/cover_letter`,
  )
  if (!response.ok) {
    throw new Error(`Failed to load cover letter (${response.status})`)
  }
  return response.text()
}

export function getDownloadUrl(applicationId: string, kind: DownloadKind): string {
  return `/api/applications/${encodeURIComponent(applicationId)}/${kind}`
}

export function getCoverLetterUrl(applicationId: string): string {
  return `/api/applications/${encodeURIComponent(applicationId)}/cover_letter`
}

export function getCoverLetterPdfUrl(applicationId: string): string {
  return `/api/applications/${encodeURIComponent(applicationId)}/cover_letter/pdf`
}
