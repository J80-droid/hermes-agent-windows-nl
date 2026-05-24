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

const TABLE_DIVIDER_CELL_RE = /^\s*:?-{3,}:?\s*$/
const PSEUDO_SEPARATOR_LINE_RE = /^[\s_\-—─]{6,}\s*$/
const ORPHAN_TRAILING_PIPE_RE = /\|\s*$/
const HEADING_LINE_RE = /^\s{0,3}#{1,6}\s+.+$/
const VERSUS_IN_HEADING_RE = /(.+?)\s+(?:versus|vs\.?|tegen)\s+(.+)/i
const INLINE_DUAL_SPLIT_RE = /_{4,}|─{4,}|\s+[—–-]{2,}\s+/
const BOLD_CATEGORY_LINE_RE = /^\*\*(?<label>[^*\n]+)\*\*\s*$/
const BOLD_CATEGORY_INLINE_RE = /^\*\*(?<label>[^*\n]+)\*\*\s+(?<rest>.+)$/
const MAX_COMPARISON_COLUMNS = 6

function splitMarkdownTableRow(row: string): string[] {
  let s = row.trim()
  if (s.startsWith('|')) s = s.slice(1)
  if (s.endsWith('|')) s = s.slice(0, -1)
  return s.split('|').map((c) => c.trim())
}

function isMarkdownTableDividerLine(row: string): boolean {
  const cells = splitMarkdownTableRow(row)
  return cells.length > 1 && cells.every((c) => TABLE_DIVIDER_CELL_RE.test(c))
}

function looksLikeMarkdownTableRow(row: string): boolean {
  if (!row.includes('|')) return false
  const stripped = row.trim()
  if (!stripped) return false
  if (stripped.startsWith('|')) return true
  return (stripped.match(/\|/g) || []).length >= 2
}

function sectionHasMarkdownTable(bodyLines: string[]): boolean {
  return bodyLines.some((line) => isMarkdownTableDividerLine(line))
}

function stripOrphanTrailingPipe(line: string): string {
  return line.replace(ORPHAN_TRAILING_PIPE_RE, '').trimEnd()
}

function sanitizeTableCell(text: string): string {
  let cell = (text || '').trim().replace(/\s+/g, ' ')
  cell = cell.replace(/_{2,}/g, ' ').trim()
  return cell
}

function renderMarkdownTable(headers: string[], rows: string[][]): string[] {
  const ncols = headers.length
  if (ncols < 2 || !rows.length) return []
  const out = [
    `| ${headers.join(' | ')} |`,
    `| ${Array(ncols).fill('---').join(' | ')} |`,
  ]
  for (const row of rows) {
    const cells = row.slice(0, ncols).map(sanitizeTableCell)
    while (cells.length < ncols) cells.push('')
    out.push(`| ${cells.join(' | ')} |`)
  }
  return out
}

function inferColumnsFromHeading(headingLine: string): string[] | null {
  let title = headingLine.replace(/^\s{0,3}#{1,6}\s+/, '').trim()
  title = title.replace(/^(?:vergelijking|comparison)\s*:\s*/i, '')
  const match = title.match(VERSUS_IN_HEADING_RE)
  if (match) {
    const a = match[1]!.trim().replace(/:$/, '')
    const b = match[2]!.trim()
    if (a && b) return ['Aspect', a, b]
  }
  return null
}

function countPseudoTableSignals(bodyLines: string[]): number {
  let signals = 0
  for (const line of bodyLines) {
    const stripped = stripOrphanTrailingPipe(line.trim())
    if (!stripped) continue
    if (PSEUDO_SEPARATOR_LINE_RE.test(stripped)) {
      signals++
      continue
    }
    if (ORPHAN_TRAILING_PIPE_RE.test(line)) signals++
    if (BOLD_CATEGORY_INLINE_RE.test(stripped) && INLINE_DUAL_SPLIT_RE.test(stripped)) signals++
    if (INLINE_DUAL_SPLIT_RE.test(stripped) && !stripped.startsWith('|')) signals++
  }
  return signals
}

const ENTITY_PREFIX_RE = /^[A-Za-z0-9 .+\-]+:\s*/

function splitLabeledEntityValue(text: string): [string | null, string] {
  const match = text.trim().match(/^([^:|]{1,40}):\s*(.+)$/)
  if (match) return [match[1]!.trim(), match[2]!.trim()]
  return [null, text.trim()]
}

function appendDualEntityRow(
  rows: string[][],
  entityHeaders: string[] | null,
  label: string,
  partA: string,
  partB: string,
): string[] | null {
  const [entityA, valueAraw] = splitLabeledEntityValue(partA)
  const [entityB, valueBraw] = splitLabeledEntityValue(partB)
  let nextHeaders = entityHeaders
  let valueA = valueAraw
  let valueB = valueBraw
  if (entityA && entityB) {
    const pair = [entityA, entityB]
    if (nextHeaders === null) nextHeaders = pair
    else if (nextHeaders[0] !== pair[0] || nextHeaders[1] !== pair[1]) nextHeaders = null
  } else {
    valueA = partA.replace(ENTITY_PREFIX_RE, '').trim()
    valueB = partB.replace(ENTITY_PREFIX_RE, '').trim()
  }
  rows.push([label, valueA, valueB])
  return nextHeaders
}

function parseComparisonBodyToRows(
  bodyLines: string[],
  defaultHeaders: string[] | null,
): { headers: string[]; rows: string[][] } | null {
  const rows: string[][] = []
  let pendingLabel: string | null = null
  let entityHeaders: string[] | null = null

  for (const line of bodyLines) {
    const stripped = stripOrphanTrailingPipe(line.trim())
    if (!stripped) continue
    if (PSEUDO_SEPARATOR_LINE_RE.test(stripped)) {
      pendingLabel = null
      continue
    }
    if (stripped.startsWith('|')) return null

    const boldOnly = stripped.match(BOLD_CATEGORY_LINE_RE)
    if (boldOnly?.groups?.label) {
      pendingLabel = boldOnly.groups.label.trim()
      continue
    }

    const boldInline = stripped.match(BOLD_CATEGORY_INLINE_RE)
    if (boldInline?.groups) {
      const label = boldInline.groups.label!.trim()
      const parts = boldInline.groups.rest!
        .trim()
        .split(INLINE_DUAL_SPLIT_RE)
        .map((p) => p.trim())
        .filter(Boolean)
      if (parts.length >= 2) rows.push([label, parts[0]!, parts[1]!])
      pendingLabel = null
      continue
    }

    if (pendingLabel) {
      const parts = stripped
        .split(INLINE_DUAL_SPLIT_RE)
        .map((p) => p.trim())
        .filter(Boolean)
      if (parts.length >= 2) {
        entityHeaders = appendDualEntityRow(
          rows,
          entityHeaders,
          pendingLabel,
          parts[0]!,
          parts[1]!,
        )
        pendingLabel = null
        continue
      }
    }

    const dash = stripped.match(NFR_CATEGORY_DASH_RE)
    if (dash && !INLINE_DUAL_SPLIT_RE.test(stripped)) {
      rows.push([
        stripMdBold(dash[1]!),
        dash[2]!.trim(),
        (dash[3] || '-').trim() || '-',
      ])
      pendingLabel = null
      continue
    }

    const labelColon = stripped.match(/^([^:|]{2,40}):\s*(.+)$/)
    if (labelColon && !pendingLabel) {
      const label = labelColon[1]!.trim()
      const rest = labelColon[2]!.trim()
      const parts = rest
        .split(INLINE_DUAL_SPLIT_RE)
        .map((p) => p.trim())
        .filter(Boolean)
      if (parts.length >= 2) {
        entityHeaders = appendDualEntityRow(rows, entityHeaders, label, parts[0]!, parts[1]!)
        continue
      }
    }
  }

  if (rows.length < 2) return null

  const maxCols = Math.min(
    MAX_COMPARISON_COLUMNS,
    Math.max(...rows.map((r) => r.length)),
  )
  if (maxCols < 2) return null

  let headers: string[]
  if (defaultHeaders && defaultHeaders.length === maxCols) {
    headers = defaultHeaders
  } else if (maxCols === 3 && entityHeaders && entityHeaders.length === 2) {
    headers = ['Aspect', entityHeaders[0]!, entityHeaders[1]!]
  } else if (maxCols === 2) {
    headers = ['Aspect', 'Optie A', 'Optie B']
  } else if (maxCols === 3 && defaultHeaders && defaultHeaders.length >= 3) {
    headers = defaultHeaders.slice(0, 3)
  } else {
    headers = ['Aspect', ...Array.from({ length: maxCols - 1 }, (_, i) => `Kolom ${i + 1}`)]
  }

  const normalizedRows = rows.map((row) => {
    const cells = row.slice(0, maxCols)
    while (cells.length < maxCols) cells.push('')
    return cells
  })

  return { headers, rows: normalizedRows }
}

function ensureMarkdownTableDividers(text: string): string {
  if (!text?.trim() || !text.includes('|')) return text || ''

  const lines = text.split('\n')
  const out: string[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]!
    if (looksLikeMarkdownTableRow(line) && !isMarkdownTableDividerLine(line)) {
      if (i + 1 < lines.length && isMarkdownTableDividerLine(lines[i + 1]!)) {
        out.push(line)
        i++
        while (i < lines.length && looksLikeMarkdownTableRow(lines[i]!)) {
          out.push(lines[i]!)
          i++
        }
        continue
      }
      if (
        i + 1 < lines.length &&
        looksLikeMarkdownTableRow(lines[i + 1]!) &&
        !isMarkdownTableDividerLine(lines[i + 1]!)
      ) {
        const headerCells = splitMarkdownTableRow(line)
        if (headerCells.length > 1 && headerCells.some((c) => c.trim())) {
          out.push(line)
          out.push(`| ${headerCells.map(() => '---').join(' | ')} |`)
          i++
          while (i < lines.length && looksLikeMarkdownTableRow(lines[i]!)) {
            if (isMarkdownTableDividerLine(lines[i]!)) {
              i++
              continue
            }
            out.push(lines[i]!)
            i++
          }
          continue
        }
      }
    }
    out.push(line)
    i++
  }

  return out.join('\n')
}

function normalizePseudoTablesToMarkdown(text: string): string {
  if (!text?.trim()) return text || ''
  if (
    !(
      text.includes('|') ||
      /_{4,}/.test(text) ||
      /^\*\*[^*]+\*\*/m.test(text) ||
      /\b(versus|vs\.?|vergelijk|comparison)\b/i.test(text)
    )
  ) {
    return text
  }

  const lines = text.split('\n')
  const out: string[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]!
    if (!HEADING_LINE_RE.test(line)) {
      out.push(line)
      i++
      continue
    }

    const heading = line
    i++
    const bodyLines: string[] = []
    while (i < lines.length && !HEADING_LINE_RE.test(lines[i]!)) {
      bodyLines.push(lines[i]!)
      i++
    }

    if (!bodyLines.length) {
      out.push(heading)
      continue
    }

    if (sectionHasMarkdownTable(bodyLines)) {
      out.push(heading)
      out.push(...bodyLines)
      continue
    }

    const defaultHeaders = inferColumnsFromHeading(heading)
    const isComparisonHeading =
      defaultHeaders !== null ||
      /\b(vergelijk|versus|vs\.?|comparison|tabel)\b/i.test(heading)
    const signals = countPseudoTableSignals(bodyLines)

    if (!isComparisonHeading && signals < 2) {
      out.push(heading)
      out.push(...bodyLines)
      continue
    }

    const parsed = parseComparisonBodyToRows(bodyLines, defaultHeaders)
    if (parsed) {
      out.push(heading)
      out.push(...renderMarkdownTable(parsed.headers, parsed.rows))
      continue
    }

    out.push(heading)
    out.push(...bodyLines)
  }

  return out.join('\n')
}

export function normalizeAssistantMarkdown(text: string): string {
  if (!text?.trim()) return text || ''

  let out = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')

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

  out = ensureMarkdownTableDividers(out)
  out = normalizePseudoTablesToMarkdown(out)

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
