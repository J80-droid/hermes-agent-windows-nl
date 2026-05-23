/** Institutional assistant markdown normalize (parity with hermes_cli/markdown_output_normalize.py). */

const HEADING_INLINE_BODY_RE =
  /^(?<prefix>\s{0,3}#{1,6}\s+)(?<title>.+?)\s+(?<body>(?:Dit|Het|De|Een|The|This|These|When|If)\s.+)$/gim

const LABEL_INLINE_VALUE_RE = /^(\s*(?:[-*+]\s+)?)\*\*([^*\n]+?):\*\*\s+(\S.+)$/gm

const SECTION_BREAK_BEFORE_HEADING_RE = /(?<!\n\n)(?<=\S\n)(#{1,6}\s)/gm

const NUMBERED_STEP_HEADING_RE = /^(\d+)\s+Stap\s+(\d+)\s*:\s*(.+?)\s*$/gim

const PLAIN_OUTLINE_H1_RE = /^(\d+)\.\s+(.+?)\s*$/gm
const BOLD_PLAIN_OUTLINE_H1_RE = /^\s*\*\*(\d+)\.\s+([^*\n]+?)\*\*\s*$/gm
const CHAPTER_NUM_SPACE_RE = /^(\d+)\s+(.+?)\s*$/gm
const DOTTED_OUTLINE_HEADING_RE = /^(\d+(?:\.\d+)+)\s+(.+?)\s*$/gm
const BOLD_DOTTED_OUTLINE_HEADING_RE = /^\s*\*\*(\d+(?:\.\d+)+)\s+([^*\n]+?)\*\*\s*$/gm

const INSTITUTIONAL_CHECK_INLINE_RE =
  /^(<institutional_check>)\s*([\s\S]*?)(<\/institutional_check>)\s*$/gim

const HEADING_TIGHT_TO_BODY_RE =
  /^(?<h>(?:\s{0,3})#{1,6}\s+[^\n]+)\n\n+(?!(?:\s{0,3})#)(?=\S)/gm
const HEADING_TIGHT_BEFORE_TABLE_RE = /^(?<h>(?:\s{0,3})#{1,6}\s+[^\n]+)\n\n+(?=\|)/gm
const LABEL_TIGHT_TO_VALUE_RE = /^(\s*(?:[-*+]\s+)?\*\*[^*\n]+:\*\*)\n\n+(?=\S)/gm

const NFR_INLINE_ROW_RE =
  /^Categorie:\s*(.+?)\s+Eis:\s*(.+?)\s+Meetmethode:\s*(.+?)\s*$/i

const LIST_ITEM_VERB_PREFIX_RE =
  /^(?:doe|do|ga|open|voer|importeer|controleer|kies|zet|voeg|stel|maak|lees|schrijf|bewaar|start|stop|gebruik|download|upload|installeer|bekijk|test|verifieer)\b/i

export const ASSISTANT_TABLE_HEADER_CLASSES = [
  'text-cyan-400',
  'text-green-400',
  'text-foreground',
  'text-fuchsia-400',
] as const

export const ASSISTANT_HEADING_CLASSES = [
  'text-cyan-400',
  'text-green-400',
  'text-yellow-400',
  'text-fuchsia-400',
  'text-foreground',
  'text-muted-foreground',
] as const

export const ASSISTANT_LABEL_CLASS = 'text-fuchsia-400 font-bold'

export const assistantWebPaletteName = (palette: string | undefined): string => palette || 'demo'

function looksLikeOutlineHeadingTitle(title: string): boolean {
  const t = title.trim()
  if (t.length < 2 || t.endsWith('.') || t.startsWith('[')) return false
  if (t[0] === t[0]?.toLowerCase() && t[0] !== t[0]?.toUpperCase()) return false
  if (LIST_ITEM_VERB_PREFIX_RE.test(t)) return false
  if (t.length > 100 || (t.match(/\. /g) || []).length > 1) return false
  return true
}

function headingLevelFromOutlineDepth(num: string): number {
  return Math.min(6, Math.max(2, num.split('.').length + 1))
}

function normalizePlainOutlineHeadings(text: string): string {
  let out = text

  out = out.replace(BOLD_DOTTED_OUTLINE_HEADING_RE, (_m, num: string, title: string) => {
    const hashes = '#'.repeat(headingLevelFromOutlineDepth(num))
    return `${hashes} ${title.trim()}`
  })

  out = out.replace(BOLD_PLAIN_OUTLINE_H1_RE, (_m, _num: string, title: string) => {
    if (!looksLikeOutlineHeadingTitle(title)) return _m
    return `## ${title.trim()}`
  })

  out = out.replace(DOTTED_OUTLINE_HEADING_RE, (_m, num: string, title: string) => {
    const hashes = '#'.repeat(headingLevelFromOutlineDepth(num))
    return `${hashes} ${title.trim()}`
  })

  out = out.replace(PLAIN_OUTLINE_H1_RE, (_m, _num: string, title: string) => {
    if (!looksLikeOutlineHeadingTitle(title)) return _m
    return `## ${title.trim()}`
  })

  out = out.replace(CHAPTER_NUM_SPACE_RE, (full, _num: string, title: string) => {
    if (!looksLikeOutlineHeadingTitle(title)) return full
    return `## ${title.trim()}`
  })

  return out
}

function ensureInstitutionalCheckBlock(text: string): string {
  return text.replace(INSTITUTIONAL_CHECK_INLINE_RE, (_m, _open: string, body: string) => {
    const lines = body
      .split('\n')
      .map((ln) => ln.trim())
      .filter(Boolean)
    return ['<institutional_check>', ...lines, '</institutional_check>'].join('\n')
  })
}

function ensureInstitutionalCheckSpacing(text: string): string {
  let out = text.replace(/(?<=\S)\n(<institutional_check>)/gi, '\n\n$1')
  out = out.replace(/(<\/institutional_check>)\n(?=\S)/gi, '$1\n\n')
  return out
}

function normalizePlainNfrRowsToTable(text: string): string {
  if (!text.includes('Categorie:')) return text

  const lines = text.split('\n')
  const out: string[] = []
  let i = 0

  while (i < lines.length) {
    const stripped = lines[i].trim()
    const match = stripped.match(NFR_INLINE_ROW_RE)
    if (match) {
      const rows: Array<[string, string, string]> = []
      while (i < lines.length) {
        const s = lines[i].trim()
        if (!s || /^[-*_]{3,}\s*$/.test(s)) {
          i++
          continue
        }
        const m = s.match(NFR_INLINE_ROW_RE)
        if (!m) break
        rows.push([m[1].trim(), m[2].trim(), m[3].trim()])
        i++
      }
      if (rows.length) {
        out.push('| Categorie | Eis | Meetmethode |', '| --- | --- | --- |')
        for (const [cat, eis, met] of rows) {
          out.push(`| ${cat} | ${eis} | ${met} |`)
        }
        continue
      }
    }
    out.push(lines[i])
    i++
  }
  return out.join('\n')
}

const NFR_SECTION_HEADING_RE = /^\s{0,3}(#{1,6}\s+Niet-functionele\s+requirements)\s*$/i
const NFR_LONG_DASH_LINE_RE = /^[\s\-_\u2013\u2014]{6,}\s*$/
const NFR_BOLD_CATEGORY_RE = /^\*\*(.+?)\*\*\s*$/
const NFR_CATEGORY_DASH_RE =
  /^(\*\*[^*]+\*\*|[^|\u2013\u2014\-\n]+?)\s*[\u2013\u2014\-:]\s*(.+?)(?:\s*[\u2013\u2014\-]\s*(.+))?\s*$/

function stripMdBold(text: string): string {
  return text.replace(/^\*\*|\*\*$/g, '').trim()
}

function parseNfrProseLines(bodyLines: string[]): Array<[string, string, string]> {
  const rows: Array<[string, string, string]> = []
  let pendingCat: string | null = null
  const pendingEis: string[] = []

  const flush = () => {
    if (pendingCat && pendingEis.length) {
      rows.push([pendingCat, pendingEis.join(' ').trim(), '-'])
    }
    pendingCat = null
    pendingEis.length = 0
  }

  for (const line of bodyLines) {
    const stripped = line.trim()
    if (!stripped || NFR_LONG_DASH_LINE_RE.test(stripped)) {
      flush()
      continue
    }
    if (stripped.startsWith('|')) break

    const bold = stripped.match(NFR_BOLD_CATEGORY_RE)
    if (bold) {
      flush()
      pendingCat = bold[1]!.trim()
      continue
    }

    const dash = stripped.match(NFR_CATEGORY_DASH_RE)
    if (dash) {
      flush()
      rows.push([
        stripMdBold(dash[1]!),
        dash[2]!.trim(),
        (dash[3] || '-').trim() || '-',
      ])
      continue
    }

    if (pendingCat) {
      pendingEis.push(stripped)
    } else if (stripped.length > 3) {
      pendingCat = stripped.replace(/:$/, '')
    }
  }
  flush()
  return rows
}

function normalizeNfrProseSectionToTable(text: string): string {
  if (!text?.trim() || !/niet-functionele/i.test(text)) return text || ''

  const lines = text.split('\n')
  const out: string[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]!
    if (!NFR_SECTION_HEADING_RE.test(line)) {
      out.push(line)
      i++
      continue
    }

    out.push(line)
    i++
    while (i < lines.length && !lines[i]!.trim()) i++

    if (i >= lines.length) break

    if (lines[i]!.trim().startsWith('|')) {
      while (i < lines.length && !/^\s{0,3}#{1,6}\s+/.test(lines[i]!)) {
        out.push(lines[i]!)
        i++
      }
      continue
    }

    const bodyLines: string[] = []
    while (i < lines.length && !/^\s{0,3}#{1,6}\s+/.test(lines[i]!)) {
      bodyLines.push(lines[i]!)
      i++
    }

    const rows = parseNfrProseLines(bodyLines)
    if (rows.length) {
      out.push('| Categorie | Eis | Meetmethode |', '| --- | --- | --- |')
      for (const [cat, eis, met] of rows) {
        out.push(`| ${cat} | ${eis} | ${met} |`)
      }
    } else {
      out.push(...bodyLines)
    }
  }

  return out.join('\n')
}

function compactInstitutionalCheck(text: string): string {
  return text.replace(
    /<institutional_check>\s*([\s\S]*?)\s*<\/institutional_check>/gi,
    (_m, body: string) => {
      const items = body
        .split('\n')
        .map((ln) => ln.trim().replace(/^[-*+]\s+/, ''))
        .filter(Boolean)
      if (!items.length) return 'Controle'
      return `Controle  · ${items.join('  · ')}`
    },
  )
}

export function normalizeAssistantMarkdown(text: string): string {
  if (!text?.trim()) return text || ''

  let out = text

  out = ensureInstitutionalCheckBlock(out)
  out = ensureInstitutionalCheckSpacing(out)

  out = out.replace(HEADING_INLINE_BODY_RE, (_m, prefix: string, title: string, body: string) => {
    return `${prefix}${title.trim()}\n\n${body.trim()}`
  })

  out = out.replace(LABEL_INLINE_VALUE_RE, (_m, lead: string, label: string, value: string) => {
    return `${lead}**${label.trim()}:**\n\n${value.trim()}`
  })

  out = out.replace(NUMBERED_STEP_HEADING_RE, (_m, _n, step: string, title: string) => `## Stap ${step}: ${title.trim()}`)

  out = normalizePlainOutlineHeadings(out)

  out = out.replace(SECTION_BREAK_BEFORE_HEADING_RE, '\n\n$1')
  out = out.replace(/(?<!\n\n)(\n)(#{1,6}\s)/g, '\n\n$2')

  out = out.replace(HEADING_TIGHT_BEFORE_TABLE_RE, '$<h>\n')
  out = out.replace(HEADING_TIGHT_TO_BODY_RE, '$<h>\n')
  out = out.replace(LABEL_TIGHT_TO_VALUE_RE, '$1\n')

  out = normalizePlainNfrRowsToTable(out)
  out = normalizeNfrProseSectionToTable(out)
  out = compactInstitutionalCheck(out)

  return out.replace(/\n{3,}/g, '\n\n')
}

export const tableHeaderClass = (index: number): string =>
  ASSISTANT_TABLE_HEADER_CLASSES[index % ASSISTANT_TABLE_HEADER_CLASSES.length]!

/** Same per-column palette on body cells (parity with CLI/Ink column tint). */
export const tableCellClass = tableHeaderClass

export const headingClass = (level: number): string =>
  ASSISTANT_HEADING_CLASSES[Math.min(Math.max(level - 1, 0), ASSISTANT_HEADING_CLASSES.length - 1)]!
