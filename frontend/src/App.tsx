import { useState } from 'react'
import {
  Button,
  Container,
  Divider,
  Group,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core'
import {
  ApplicationApiError,
  type ApplicationResponse,
  createApplication,
  type FatalPhaseError,
  getLlmsResponse,
} from './api/client'
import { ExportMenu } from './components/ExportMenu'
import { PhaseChips } from './components/PhaseChips'

interface FormValues {
  job_position: string
  company_name: string
  company_description: string
  job_description: string
}

const EMPTY_FORM: FormValues = {
  job_position: '',
  company_name: '',
  company_description: '',
  job_description: '',
}

export default function App() {
  const [values, setValues] = useState<FormValues>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [response, setResponse] = useState<ApplicationResponse | null>(null)
  const [fatal, setFatal] = useState<FatalPhaseError | null>(null)
  const [llmText, setLlmText] = useState<string | null>(null)
  const [llmError, setLlmError] = useState<string | null>(null)

  const canSubmit =
    values.job_position.trim() !== '' &&
    values.company_name.trim() !== '' &&
    values.job_description.trim() !== ''

  function setField(field: keyof FormValues, value: string): void {
    setValues((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(): Promise<void> {
    setSubmitting(true)
    setFatal(null)
    setResponse(null)
    setLlmText(null)
    setLlmError(null)
    try {
      const result = await createApplication({
        job_position: values.job_position.trim(),
        company_name: values.company_name.trim(),
        company_description: values.company_description.trim() || null,
        job_description: values.job_description.trim(),
      })
      setResponse(result)
      try {
        setLlmText(await getLlmsResponse(result.application_id))
      } catch {
        setLlmError('Could not load the LLM response.')
      }
    } catch (error) {
      if (error instanceof ApplicationApiError) {
        setFatal({ phase: error.phase, error: error.message })
      } else {
        setFatal({ phase: 'reconstruction', error: 'Unexpected error while generating.' })
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container size="sm" px="lg" py="xl">
      <Title order={1} size="h2">
        Resume Pipeline
      </Title>
      <Text c="dark.2" size="sm" mt={4}>
        Generate a tailored LaTeX resume from a single job description.
      </Text>

      <Divider my="xl" color="dark.6" />

      <Stack gap="sm">
        <TextInput
          label="Job position"
          placeholder="e.g. Senior Software Engineer"
          value={values.job_position}
          onChange={(event) => setField('job_position', event.currentTarget.value)}
        />
        <TextInput
          label="Company name"
          placeholder="e.g. Acme Corp"
          value={values.company_name}
          onChange={(event) => setField('company_name', event.currentTarget.value)}
        />
        <TextInput
          label="Company description (optional)"
          placeholder="One or two lines about what the company does"
          value={values.company_description}
          onChange={(event) => setField('company_description', event.currentTarget.value)}
        />
        <Textarea
          label="Job description"
          placeholder="Paste the job posting here"
          minRows={6}
          autosize
          value={values.job_description}
          onChange={(event) => setField('job_description', event.currentTarget.value)}
        />
        <Button onClick={handleSubmit} loading={submitting} disabled={!canSubmit} radius={0} fullWidth mt="md">
          Generate resume
        </Button>
      </Stack>

      <Divider my="xl" color="dark.6" />

      <Stack gap="xs">
        <Text fw={500} size="sm" c="dark.1">
          Phases
        </Text>
        <PhaseChips response={response} fatal={fatal} />
        {fatal && (
          <Text size="sm" c="red.7" mt={4}>
            {fatal.phase}: {fatal.error}
          </Text>
        )}
      </Stack>

      <Divider my="xl" color="dark.6" />

      {llmText !== null || llmError !== null ? (
        <Stack gap="xs">
          <Text fw={500} size="sm" c="dark.1">
            LLM response
          </Text>
          <Textarea
            readOnly
            minRows={10}
            autosize
            value={llmText ?? ''}
            placeholder="No response text."
            style={{ fontFamily: 'var(--mantine-font-family-monospace)' }}
          />
          {llmError && (
            <Text size="xs" c="red.7">
              {llmError}
            </Text>
          )}
        </Stack>
      ) : (
        <Text size="sm" c="dark.3">
          The raw LLM response appears here after a successful run.
        </Text>
      )}

      <Divider my="xl" color="dark.6" />

      <Group justify="space-between" align="center">
        <Stack gap={2}>
          <Text fw={500} size="sm" c="dark.1">
            Export
          </Text>
          <Text size="xs" c="dark.3">
            {response
              ? `resume-${response.application_id}.tex / .pdf`
              : 'Available after a successful run.'}
          </Text>
        </Stack>
        <ExportMenu applicationId={response?.application_id ?? null} />
      </Group>
    </Container>
  )
}
