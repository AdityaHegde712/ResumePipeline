import { useRef, useState } from 'react'
import { Alert, Button, Group, Stack, Text, Textarea } from '@mantine/core'
import { getCoverLetterPdfUrl } from '../api/client'

interface CoverLetterSectionProps {
  applicationId: string
  text: string | null
  alert: string | null
  generating: boolean
  showGenerate: boolean
  onGenerate: () => void
}

export function CoverLetterSection({
  applicationId,
  text,
  alert,
  generating,
  showGenerate,
  onGenerate,
}: CoverLetterSectionProps) {
  const [copied, setCopied] = useState(false)
  const copyTimer = useRef<number | null>(null)

  async function handleCopy(): Promise<void> {
    if (text === null) {
      return
    }
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      if (copyTimer.current !== null) {
        window.clearTimeout(copyTimer.current)
      }
      copyTimer.current = window.setTimeout(() => setCopied(false), 1500)
    } catch {
      // Clipboard unavailable (e.g. insecure context) — no confirmation.
    }
  }

  function openPdf(): void {
    window.open(getCoverLetterPdfUrl(applicationId), '_blank')
  }

  const hasLetter = text !== null

  return (
    <Stack gap="xs">
      <Text fw={500} size="sm" c="dark.1">
        Cover letter
      </Text>
      {alert && (
        <Alert color="red" variant="light" p="sm">
          <Text size="sm" c="red.7">
            {alert}
          </Text>
        </Alert>
      )}
      {hasLetter ? (
        <>
          <Textarea readOnly minRows={10} autosize value={text} placeholder="Cover letter text." />
          <Group gap="xs">
            <Button variant="outline" fw={400} radius={0} onClick={handleCopy} disabled={text === ''}>
              {copied ? 'Copied' : 'Copy'}
            </Button>
            <Button variant="outline" fw={400} radius={0} onClick={openPdf}>
              Export PDF
            </Button>
          </Group>
        </>
      ) : showGenerate ? (
        <Button
          variant="outline"
          fw={400}
          radius={0}
          onClick={onGenerate}
          loading={generating}
          style={{ alignSelf: 'flex-start' }}
        >
          Generate cover letter
        </Button>
      ) : null}
    </Stack>
  )
}
