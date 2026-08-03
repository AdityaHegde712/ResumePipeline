import { colorsTuple, createTheme } from '@mantine/core'

// Muted blue-gray accent (never loud); used for filled buttons and focus rings.
const accent = colorsTuple([
  '#EAF1F7',
  '#D7E3EC',
  '#B9CFDE',
  '#97B5C9',
  '#7399B0',
  '#5A829A',
  '#4A6E86',
  '#3D5B70',
  '#314A5B',
  '#253847',
])

// Flat dark palette per PLAN §7: #121212 body, #e0e0e0 text, 1px hairlines.
// dark[7] feeds --mantine-color-body in the dark color scheme.
export const theme = createTheme({
  primaryColor: 'accent',
  defaultRadius: 0,
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  fontFamilyMonospace:
    'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
  colors: {
    dark: colorsTuple([
      '#E0E0E0', // primary text
      '#C9C9C9', // secondary text
      '#A3A3A3', // muted text
      '#808080', // placeholders
      '#5C5C5C', // input borders
      '#3A3A3A', // strong hairline
      '#2A2A2A', // hairline dividers / hover surfaces
      '#121212', // body background
      '#161616', // elevated surface
      '#0C0C0C', // deepest surface
    ]),
    accent,
  },
  shadows: {
    xs: 'none',
    sm: 'none',
    md: 'none',
    lg: 'none',
    xl: 'none',
  },
})
