/** Institutional assistant markdown normalize + display tokens (web). */

const HEADING_INLINE_BODY_RE =
  /^(?<prefix>\s{0,3}#{1,6}\s+)(?<title>.+?)\s+(?<body>(?:Dit|Het|De|Een|Bij|In|Op|Na|Voor|The|This|These|When|If)\s.+)$/gim

const LABEL_INLINE_VALUE_RE = /^(\s*(?:[-*+]\s+)?)\*\*([^*\n]+?):\*\*\s+(\S.+)$/gm

const SECTION_BREAK_BEFORE_HEADING_RE = /(?<!\n\n)(?<=\S\n)(#{1,6}\s)/gm

const NUMBERED_STEP_HEADING_RE = /^(\d+)\s+Stap\s+(\d+)\s*:\s*(.+?)\s*$/gim

export const ASSISTANT_TABLE_HEADER_CLASSES = [
  'text-cyan-400',
  'text-green-400',
  'text-fuchsia-400',
  'text-yellow-400',
] as const

export const ASSISTANT_HEADING_CLASSES = [
  'text-cyan-400',
  'text-green-400',
  'text-fuchsia-400',
  'text-yellow-400',
  'text-foreground',
  'text-muted-foreground',
] as const

export const ASSISTANT_LABEL_CLASS = 'text-fuchsia-400 font-bold'

export function normalizeAssistantMarkdown(text: string): string {
  if (!text?.trim()) {
    return text || ''
  }

  let out = text

  out = out.replace(HEADING_INLINE_BODY_RE, (_m, prefix: string, title: string, body: string) => {
    return `${prefix}${title.trim()}\n\n${body.trim()}`
  })

  out = out.replace(LABEL_INLINE_VALUE_RE, (_m, lead: string, label: string, value: string) => {
    return `${lead}**${label.trim()}:**\n\n${value.trim()}`
  })

  out = out.replace(NUMBERED_STEP_HEADING_RE, (_m, _n, step: string, title: string) => `## Stap ${step}: ${title.trim()}`)

  out = out.replace(SECTION_BREAK_BEFORE_HEADING_RE, '\n\n$1')
  out = out.replace(/(?<!\n\n)(\n)(#{1,6}\s)/g, '\n\n$2')

  return out.replace(/\n{3,}/g, '\n\n')
}

export const tableHeaderClass = (index: number): string =>
  ASSISTANT_TABLE_HEADER_CLASSES[index % ASSISTANT_TABLE_HEADER_CLASSES.length]!

export const headingClass = (level: number): string =>
  ASSISTANT_HEADING_CLASSES[Math.min(Math.max(level - 1, 0), ASSISTANT_HEADING_CLASSES.length - 1)]!
