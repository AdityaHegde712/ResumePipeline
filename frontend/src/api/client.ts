// Typed fetch wrapper for the Resume Pipeline backend (PLAN §3, D10/D13).

export interface ApplicationResponse {
  status: number
  llm_generation: 'OK'
  reconstruction: 'OK'
  saved: 'OK'
  pdf_error: string | null
  application_id: string
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

export function getDownloadUrl(applicationId: string, kind: DownloadKind): string {
  return `/api/applications/${encodeURIComponent(applicationId)}/${kind}`
}
