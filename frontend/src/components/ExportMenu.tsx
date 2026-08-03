import { Button, Menu, Text } from '@mantine/core'
import { getDownloadUrl } from '../api/client'

interface ExportMenuProps {
  applicationId: string | null
}

function triggerDownload(url: string): void {
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = ''
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

export function ExportMenu({ applicationId }: ExportMenuProps) {
  const disabled = applicationId === null

  return (
    <Menu shadow="none" radius={0} position="bottom-end" offset={4}>
      <Menu.Target>
        <Button
          variant="outline"
          radius={0}
          fw={400}
          disabled={disabled}
          rightSection={
            <Text component="span" size="xs" c="dark.2" aria-hidden="true">
              ▾
            </Text>
          }
        >
          Export
        </Button>
      </Menu.Target>
      <Menu.Dropdown style={{ border: '1px solid var(--mantine-color-dark-6)' }}>
        <Menu.Item
          disabled={disabled}
          onClick={() => {
            if (applicationId) triggerDownload(getDownloadUrl(applicationId, 'tex'))
          }}
        >
          TeX source (.tex)
        </Menu.Item>
        <Menu.Item
          disabled={disabled}
          onClick={() => {
            if (applicationId) triggerDownload(getDownloadUrl(applicationId, 'pdf'))
          }}
        >
          PDF (.pdf)
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  )
}
