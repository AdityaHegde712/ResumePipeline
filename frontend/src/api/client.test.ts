import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ApplicationApiError,
  createApplication,
  getDownloadUrl,
  getLlmsResponse,
} from './client'

interface MockResponse {
  ok: boolean
  status: number
  json: () => Promise<unknown>
  text?: () => Promise<string>
}

function okResponse(payload: unknown, status = 200): MockResponse {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  }
}

const BASIC_BODY = {
  job_position: 'Engineer',
  company_name: 'Acme',
  job_description: 'Build things.',
}

describe('createApplication', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('POSTs JSON with the expected body and headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      okResponse({
        status: 200,
        llm_generation: 'OK',
        reconstruction: 'OK',
        saved: 'OK',
        pdf_error: null,
        application_id: 'application-20260803-010000',
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await createApplication(BASIC_BODY)

    expect(fetchMock).toHaveBeenCalledWith('/api/applications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(BASIC_BODY),
    })
  })

  it('parses a successful response including a non-fatal pdf_error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        okResponse({
          status: 200,
          llm_generation: 'OK',
          reconstruction: 'OK',
          saved: 'OK',
          pdf_error: 'pdflatex missing',
          application_id: 'application-20260803-010000',
        }),
      ),
    )

    const result = await createApplication(BASIC_BODY)

    expect(result.application_id).toBe('application-20260803-010000')
    expect(result.llm_generation).toBe('OK')
    expect(result.pdf_error).toBe('pdflatex missing')
  })

  it('throws ApplicationApiError with phase and message on a fatal 500', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(okResponse({ phase: 'llm_generation', error: 'LLM auth failed' }, 500)),
    )

    const error = await createApplication(BASIC_BODY).catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApplicationApiError)
    if (error instanceof ApplicationApiError) {
      expect(error.phase).toBe('llm_generation')
      expect(error.message).toBe('LLM auth failed')
    }
  })

  it('defaults phase and message when the 500 body is not JSON', async () => {
    const brokenResponse: MockResponse = {
      ok: false,
      status: 500,
      json: async () => {
        throw new Error('invalid json')
      },
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(brokenResponse))

    const error = await createApplication(BASIC_BODY).catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApplicationApiError)
    if (error instanceof ApplicationApiError) {
      expect(error.phase).toBe('reconstruction')
      expect(error.message).toBe('Unknown server error')
    }
  })
})

describe('getLlmsResponse', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns the raw response text', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: async () => '# Skills\n',
      } as MockResponse),
    )

    const text = await getLlmsResponse('application-20260803-010000')

    expect(text).toBe('# Skills\n')
  })

  it('throws when the response file is missing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 404, text: async () => '' } as MockResponse),
    )

    await expect(getLlmsResponse('application-missing')).rejects.toThrow(
      'Failed to load LLM response (404)',
    )
  })
})

describe('getDownloadUrl', () => {
  it('builds tex and pdf download urls', () => {
    expect(getDownloadUrl('application-1', 'tex')).toBe('/api/applications/application-1/tex')
    expect(getDownloadUrl('application-1', 'pdf')).toBe('/api/applications/application-1/pdf')
  })

  it('encodes application ids', () => {
    expect(getDownloadUrl('application/1', 'tex')).toBe('/api/applications/application%2F1/tex')
  })
})
