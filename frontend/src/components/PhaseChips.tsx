import { Box, Group, Text } from '@mantine/core'
import type { ApplicationResponse, FatalPhaseError } from '../api/client'

export type ChipPhase = 'llm_generation' | 'reconstruction' | 'saved' | 'pdf_error'

const PHASE_ORDER: ChipPhase[] = ['llm_generation', 'reconstruction', 'saved', 'pdf_error']

const PHASE_LABELS: Record<ChipPhase, string> = {
  llm_generation: 'LLM generation',
  reconstruction: 'Reconstruction',
  saved: 'Saved',
  pdf_error: 'PDF',
}

type ChipTone = 'ok' | 'fail' | 'pending'

const GLYPH: Record<ChipTone, string> = { ok: '✓', fail: '✕', pending: '–' }
const GLYPH_COLOR: Record<ChipTone, string> = {
  ok: '#5FAF66',
  fail: '#D97A7A',
  pending: '#5C5C5C',
}

function chipTone(
  phase: ChipPhase,
  response: ApplicationResponse | null,
  fatal: FatalPhaseError | null,
): ChipTone {
  if (fatal) {
    return phase === fatal.phase ? 'fail' : 'pending'
  }
  if (!response) {
    return 'pending'
  }
  if (phase === 'pdf_error') {
    return response.pdf_error ? 'fail' : 'ok'
  }
  return response[phase] === 'OK' ? 'ok' : 'fail'
}

interface PhaseChipsProps {
  response: ApplicationResponse | null
  fatal: FatalPhaseError | null
}

export function PhaseChips({ response, fatal }: PhaseChipsProps) {
  return (
    <Group gap="xs" wrap="wrap">
      {PHASE_ORDER.map((phase) => {
        const tone = chipTone(phase, response, fatal)
        return (
          <Box
            key={phase}
            component="span"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '4px 10px',
              border: '1px solid var(--mantine-color-dark-6)',
              color: 'var(--mantine-color-dark-1)',
              fontSize: 'var(--mantine-font-size-sm)',
              lineHeight: 'var(--mantine-line-height-sm)',
              whiteSpace: 'nowrap',
            }}
          >
            {PHASE_LABELS[phase]}
            <Text
              component="span"
              size="sm"
              style={{ color: GLYPH_COLOR[tone], lineHeight: 1 }}
              aria-hidden="true"
            >
              {GLYPH[tone]}
            </Text>
          </Box>
        )
      })}
    </Group>
  )
}
