import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ApplicationApiError,
  CoverLetterConflictError,
  createApplication,
  generateCoverLetter,
  getCoverLetterPdfUrl,
  getCoverLetterText,
  getCoverLetterUrl,
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

describe('createApplication cover letter body and response', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends generate_cover_letter when provided', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      okResponse({
        status: 200,
        llm_generation: 'OK',
        reconstruction: 'OK',
        saved: 'OK',
        pdf_error: null,
        application_id: 'application-20260803-010000',
        cover_letter: 'OK',
        cover_letter_generated: true,
        cover_letter_error: null,
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await createApplication({ ...BASIC_BODY, generate_cover_letter: true })

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(init.body).toBe(JSON.stringify({ ...BASIC_BODY, generate_cover_letter: true }))
  })

  it('parses cover letter fields from a successful response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        okResponse({
          status: 200,
          llm_generation: 'OK',
          reconstruction: 'OK',
          saved: 'OK',
          pdf_error: null,
          application_id: 'application-20260803-010000',
          cover_letter: 'ERROR',
          cover_letter_generated: false,
          cover_letter_error: 'LLM auth failed',
        }),
      ),
    )

    const result = await createApplication(BASIC_BODY)

    expect(result.cover_letter).toBe('ERROR')
    expect(result.cover_letter_generated).toBe(false)
    expect(result.cover_letter_error).toBe('LLM auth failed')
  })

  it('keeps cover letter fields null when generation was not requested', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        okResponse({
          status: 200,
          llm_generation: 'OK',
          reconstruction: 'OK',
          saved: 'OK',
          pdf_error: null,
          application_id: 'application-20260803-010000',
          cover_letter: null,
          cover_letter_generated: false,
          cover_letter_error: null,
        }),
      ),
    )

    const result = await createApplication(BASIC_BODY)

    expect(result.cover_letter).toBeNull()
    expect(result.cover_letter_generated).toBe(false)
    expect(result.cover_letter_error).toBeNull()
  })
})

describe('generateCoverLetter', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('POSTs the late endpoint and returns the generated letter', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      okResponse({
        cover_letter: 'OK',
        cover_letter_generated: true,
        cover_letter_text: 'Dear Hiring Manager, ...',
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const result = await generateCoverLetter('application-20260803-010000')

    expect(fetchMock).toHaveBeenCalledWith('/api/applications/application-20260803-010000/cover_letter', {
      method: 'POST',
    })
    expect(result.cover_letter).toBe('OK')
    expect(result.cover_letter_generated).toBe(true)
    expect(result.cover_letter_text).toBe('Dear Hiring Manager, ...')
  })

  it('throws CoverLetterConflictError on 409', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(okResponse({ detail: 'cover_letter.md already exists' }, 409)),
    )

    const error = await generateCoverLetter('application-1').catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(CoverLetterConflictError)
  })

  it('throws a plain error on other failures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(okResponse({ detail: 'boom' }, 500)),
    )

    await expect(generateCoverLetter('application-1')).rejects.toThrow(
      'Failed to generate cover letter (500)',
    )
  })

  it('encodes application ids in the request url', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      okResponse({ cover_letter: 'OK', cover_letter_generated: true, cover_letter_text: 'x' }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await generateCoverLetter('application/1')

    expect(fetchMock).toHaveBeenCalledWith('/api/applications/application%2F1/cover_letter', {
      method: 'POST',
    })
  })
})

describe('getCoverLetterText', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns the raw letter text', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: async () => 'Dear Hiring Manager,\n\n...',
      } as MockResponse),
    )

    const text = await getCoverLetterText('application-20260803-010000')

    expect(text).toBe('Dear Hiring Manager,\n\n...')
  })

  it('throws when the letter file is missing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 404, text: async () => '' } as MockResponse),
    )

    await expect(getCoverLetterText('application-missing')).rejects.toThrow(
      'Failed to load cover letter (404)',
    )
  })
})

describe('getCoverLetterUrl and getCoverLetterPdfUrl', () => {
  it('builds text and pdf cover letter urls', () => {
    expect(getCoverLetterUrl('application-1')).toBe(
      '/api/applications/application-1/cover_letter',
    )
    expect(getCoverLetterPdfUrl('application-1')).toBe(
      '/api/applications/application-1/cover_letter/pdf',
    )
  })

  it('encodes application ids', () => {
    expect(getCoverLetterUrl('application/1')).toBe(
      '/api/applications/application%2F1/cover_letter',
    )
    expect(getCoverLetterPdfUrl('application/1')).toBe(
      '/api/applications/application%2F1/cover_letter/pdf',
    )
  })
})
