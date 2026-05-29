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
  /^(\*\*[^*]+\*\*|[^|\u2013\u2014\n-]+?)\s*[\u2013\u2014:-]\s*(.+?)(?:\s*[\u2013\u2014-]\s*(.+))?\s*$/

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
// No bare "samenvatting" — avoids overview intent on prose like "beknopte samenvatting".
const OVERVIEW_HEADING_HINT_RE =
  /\b(overzicht|auxiliary|configuratie|stack|architectuur|architectuursamenvatting|implementatie|testresultaten|poc)\b/i
const OVERVIEW_FIELD_LINE_RE = /^([^:|]{1,48}):\s*(.+)$/i
const FIELD_KEY_TOKEN_RE = /\b([A-Za-z][A-Za-z0-9-]{0,39}):\s/gi
const FIELD_KEY_TOKEN_COUNT_RE = /\b[A-Za-z][A-Za-z0-9-]{0,39}:\s/gi
const FIELD_KEY_TOKEN_LINE_RE = /\b[A-Za-z][A-Za-z0-9-]{0,39}:\s/i
const FIELD_REPEAT_GATE_RE =
  /(?:component|keuze|status|categorie|eis|meetmethode)\s*:/gi
const CATEGORY_HEADER_NAMES = new Set(['category', 'categorie', 'taak', 'task', 'aspect'])

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
  cell = cell.replace(/_{2,}/g, ' ').replace(/\|/g, ' / ').trim()
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
    if (line.includes('|') && ORPHAN_TRAILING_PIPE_RE.test(line)) signals++
    if (
      stripped.includes('**') &&
      BOLD_CATEGORY_INLINE_RE.test(stripped) &&
      INLINE_DUAL_SPLIT_RE.test(stripped)
    ) {
      signals++
    }
    if (INLINE_DUAL_SPLIT_RE.test(stripped) && !stripped.startsWith('|')) signals++
    if (stripped.includes(':') && OVERVIEW_FIELD_LINE_RE.test(stripped)) signals++
    const labelCount = stripped.includes(':')
      ? stripped.match(FIELD_KEY_TOKEN_COUNT_RE)?.length ?? 0
      : 0
    if (labelCount >= 3) signals++
    if (stripped.includes('**') && BOLD_CATEGORY_LINE_RE.test(stripped)) signals++
  }
  return signals
}

function discoverRepeatedFieldKeys(text: string): string[] | null {
  if (!text?.trim()) return null
  const counts = new Map<string, number>()
  const order: string[] = []
  const seenLow = new Set<string>()
  FIELD_KEY_TOKEN_RE.lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = FIELD_KEY_TOKEN_RE.exec(text)) !== null) {
    const key = normalizeFieldKey(match[1]!)
    const low = key.toLowerCase()
    if (!key || key.length < 2) continue
    counts.set(low, (counts.get(low) ?? 0) + 1)
    if (!seenLow.has(low)) {
      seenLow.add(low)
      order.push(key)
    }
  }
  const repeated = order.filter((k) => (counts.get(k.toLowerCase()) ?? 0) >= 2)
  if (repeated.length < 2) return null
  return repeated.slice(0, MAX_COMPARISON_COLUMNS)
}

function splitRecordSegments(
  full: string,
  keys: string[],
  lineChunks: string[],
): string[] {
  const segments = full.split(INLINE_DUAL_SPLIT_RE).map((p) => p.trim()).filter(Boolean)
  if (segments.length >= 2) return segments
  if (
    lineChunks.length >= 2 &&
    lineChunks.every((ln) => FIELD_KEY_TOKEN_LINE_RE.test(ln))
  ) {
    return lineChunks
  }
  if (keys.length) {
    const anchor = keys[0]!.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const parts = full
      .split(new RegExp(`(?=\\b${anchor}\\s*:)`, 'i'))
      .map((p) => p.trim())
      .filter(Boolean)
    if (parts.length >= 2) return parts
  }
  return full.trim() ? [full] : []
}

function dedupeTableRows(rows: string[][]): string[][] {
  const seen = new Set<string>()
  const unique: string[][] = []
  for (const row of rows) {
    const key = row.join('\x1f')
    if (seen.has(key)) continue
    seen.add(key)
    unique.push(row)
  }
  return unique
}

function collapsedRecordLayoutEligible(chunks: string[], full: string): boolean {
  if (INLINE_DUAL_SPLIT_RE.test(full)) return true
  if (chunks.some((ln) => (ln.match(FIELD_KEY_TOKEN_COUNT_RE) ?? []).length >= 3)) return true
  if (
    chunks.length >= 2 &&
    chunks.every((ln) => FIELD_KEY_TOKEN_LINE_RE.test(ln)) &&
    !chunks.some((ln) => BOLD_CATEGORY_LINE_RE.test(ln))
  ) {
    return true
  }
  return false
}

function parseCollapsedRecordRows(
  bodyLines: string[],
  fieldKeys?: string[] | null,
): { headers: string[]; rows: string[][] } | null {
  const chunks: string[] = []
  for (const line of bodyLines) {
    const stripped = stripOrphanTrailingPipe(line.trim())
    if (!stripped || PSEUDO_SEPARATOR_LINE_RE.test(stripped)) continue
    if (stripped.startsWith('|') && looksLikeMarkdownTableRow(stripped)) return null
    chunks.push(stripped)
  }
  if (!chunks.length) return null
  const full = chunks.join(' ')
  if (!collapsedRecordLayoutEligible(chunks, full)) return null
  const keys = fieldKeys ?? discoverRepeatedFieldKeys(full)
  if (!keys || keys.length < 2) return null
  const segments = splitRecordSegments(full, keys, chunks)
  const rows: string[][] = []
  for (const segment of segments) {
    const values = extractFieldValuesFromText(segment, keys)
    const filled = keys.filter((k) => (values[k] ?? '').trim()).length
    if (filled >= 2) {
      rows.push(keys.map((k) => sanitizeTableCell(values[k] ?? '-')))
    }
  }
  const uniqueRows = dedupeTableRows(rows)
  if (uniqueRows.length < 2) return null
  return { headers: keys, rows: uniqueRows }
}

function normalizeFieldKey(key: string): string {
  return (key || '').trim().replace(/\s+/g, ' ')
}

function fieldKeyMatches(header: string, key: string): boolean {
  return normalizeFieldKey(header).toLowerCase() === normalizeFieldKey(key).toLowerCase()
}

function inferSectionIntent(headingLine: string, bodyLines: string[]): string {
  if (inferColumnsFromHeading(headingLine)) return 'comparison'
  if (OVERVIEW_HEADING_HINT_RE.test(headingLine)) return 'overview'
  if (/\b(vergelijk|versus|vs\.?|comparison|tabel)\b/i.test(headingLine)) return 'comparison'
  for (const line of bodyLines) {
    const stripped = line.trim()
    if (!stripped || PSEUDO_SEPARATOR_LINE_RE.test(stripped)) continue
    if (looksLikeMarkdownTableRow(stripped) && !isMarkdownTableDividerLine(stripped)) {
      return 'explicit_grid'
    }
    break
  }
  return 'generic'
}

function collectOverviewFieldKeys(bodyLines: string[]): string[] {
  const keys: string[] = []
  const seen = new Set<string>()
  for (const line of bodyLines) {
    const stripped = line.trim()
    if (!stripped || PSEUDO_SEPARATOR_LINE_RE.test(stripped)) continue
    if (BOLD_CATEGORY_LINE_RE.test(stripped)) continue
    const match = stripped.match(OVERVIEW_FIELD_LINE_RE)
    if (!match) continue
    const key = normalizeFieldKey(match[1]!)
    const low = key.toLowerCase()
    if (key && !seen.has(low)) {
      seen.add(low)
      keys.push(key)
    }
  }
  return keys
}

function overviewHeadersFromBody(bodyLines: string[]): string[] | null {
  for (const line of bodyLines) {
    const stripped = stripOrphanTrailingPipe(line.trim())
    if (!stripped || PSEUDO_SEPARATOR_LINE_RE.test(stripped)) continue
    if (looksLikeMarkdownTableRow(stripped) && !isMarkdownTableDividerLine(stripped)) {
      const cells = splitMarkdownTableRow(stripped)
        .map(sanitizeTableCell)
        .filter((c) => c.trim())
      if (cells.length >= 2 && cells.some(Boolean)) return cells.slice(0, MAX_COMPARISON_COLUMNS)
    }
    break
  }
  let fieldKeys = collectOverviewFieldKeys(bodyLines)
  if (fieldKeys.length < 2) {
    const joined = bodyLines
      .map((ln) => stripOrphanTrailingPipe(ln.trim()))
      .filter((ln) => ln && !PSEUDO_SEPARATOR_LINE_RE.test(ln))
      .join(' ')
    const discovered = discoverRepeatedFieldKeys(joined)
    if (!discovered) return null
    fieldKeys = discovered
  }
  if (CATEGORY_HEADER_NAMES.has(fieldKeys[0]!.toLowerCase())) {
    return fieldKeys.slice(0, MAX_COMPARISON_COLUMNS)
  }
  return (['Categorie', ...fieldKeys]).slice(0, MAX_COMPARISON_COLUMNS)
}

function extractFieldValuesFromText(text: string, fieldKeys: string[]): Record<string, string> {
  const values: Record<string, string> = {}
  const keys = fieldKeys.slice(0, MAX_COMPARISON_COLUMNS)
  for (const key of keys) {
    const others = keys
      .filter((k) => k.toLowerCase() !== key.toLowerCase())
      .map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      .join('|')
    const lookahead = others ? `(?=\\s+(?:${others})\\s*:|$)` : '$'
    const pattern = new RegExp(
      `${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*:\\s*(.+?)${lookahead}`,
      'i',
    )
    const match = text.match(pattern)
    if (match?.[1]) values[key] = match[1].trim()
  }
  return values
}

function parseOverviewFieldRows(bodyLines: string[], headers: string[]): string[][] | null {
  if (headers.length < 2) return null
  const fieldKeys = CATEGORY_HEADER_NAMES.has(headers[0]!.toLowerCase())
    ? headers.slice(1)
    : headers
  const categoryInHeaders = CATEGORY_HEADER_NAMES.has(headers[0]!.toLowerCase())
  const rows: string[][] = []
  let category = ''
  let values: Record<string, string> = {}

  const flush = () => {
    if (!category && !Object.values(values).some((v) => v.trim() && v !== '-')) return
    const row = categoryInHeaders
      ? [category || '-', ...fieldKeys.map((key) => values[key] ?? '-')]
      : headers.map((key) => values[key] ?? '-')
    rows.push(row)
    category = ''
    values = {}
  }

  for (const line of bodyLines) {
    const stripped = stripOrphanTrailingPipe(line.trim())
    if (!stripped) continue
    if (PSEUDO_SEPARATOR_LINE_RE.test(stripped)) {
      flush()
      continue
    }
    if (stripped.startsWith('|') && looksLikeMarkdownTableRow(stripped)) continue

    const boldOnly = stripped.match(BOLD_CATEGORY_LINE_RE)
    if (boldOnly?.groups?.label) {
      flush()
      category = boldOnly.groups.label.trim()
      continue
    }

    const fieldMatch = stripped.match(OVERVIEW_FIELD_LINE_RE)
    if (fieldMatch) {
      const key = normalizeFieldKey(fieldMatch[1]!)
      const val = fieldMatch[2]!.trim()
      for (const hdr of fieldKeys) {
        if (fieldKeyMatches(hdr, key)) {
          values[hdr] = val
          break
        }
      }
      continue
    }

    const inlineVals = extractFieldValuesFromText(stripped, fieldKeys)
    if (Object.keys(inlineVals).length) Object.assign(values, inlineVals)
  }

  flush()
  return rows.length >= 2 ? rows : null
}

function parseCollapsedOverviewBody(
  bodyLines: string[],
): { headers: string[]; rows: string[][] } | null {
  const chunks: string[] = []
  for (const line of bodyLines) {
    const stripped = stripOrphanTrailingPipe(line.trim())
    if (!stripped || PSEUDO_SEPARATOR_LINE_RE.test(stripped)) continue
    chunks.push(stripped)
  }
  if (!chunks.length) return null
  const full = chunks.join(' ')

  const headerMatch = full.match(
    /^((?:[A-Za-z][A-Za-z0-9 /]{0,40}\s*\|\s*){1,}[A-Za-z][A-Za-z0-9 /]{0,40})/,
  )
  if (headerMatch) {
    const headerPart = headerMatch[1]!
    const headers = splitMarkdownTableRow(headerPart)
      .map(sanitizeTableCell)
      .filter((c) => c.trim())
    if (headers.length >= 2) {
      const remainder = full.slice(headerMatch[0].length).trim()
      const fieldKeys = CATEGORY_HEADER_NAMES.has(headers[0]!.toLowerCase())
        ? headers.slice(1)
        : headers
      const parts = remainder.split(/\*\*([^*]+)\*\*/)
      const rows: string[][] = []
      if (parts.length >= 3) {
        for (let idx = 1; idx < parts.length; idx += 2) {
          const label = parts[idx]!.trim()
          const content = parts[idx + 1]?.trim() ?? ''
          const vals = extractFieldValuesFromText(content, fieldKeys)
          if (CATEGORY_HEADER_NAMES.has(headers[0]!.toLowerCase())) {
            rows.push([label, ...fieldKeys.map((key) => vals[key] ?? '-')])
          } else {
            rows.push(headers.map((key) => vals[key] ?? '-'))
          }
        }
      }
      if (rows.length >= 2) {
        return { headers: headers.slice(0, MAX_COMPARISON_COLUMNS), rows }
      }
    }
  }

  const recordParsed = parseCollapsedRecordRows(bodyLines)
  if (recordParsed) return recordParsed

  const headers = overviewHeadersFromBody(bodyLines)
  if (!headers) return null
  const rows = parseOverviewFieldRows(bodyLines, headers)
  return rows ? { headers, rows } : null
}

function parseExplicitHeaderGrid(
  bodyLines: string[],
): { headers: string[]; rows: string[][] } | null {
  const substantive = bodyLines
    .map((ln) => ln.trim())
    .filter((ln) => ln && !PSEUDO_SEPARATOR_LINE_RE.test(ln))
  if (substantive.length < 2) return null
  if (!substantive.every((ln) => looksLikeMarkdownTableRow(ln))) return null
  const headers = splitMarkdownTableRow(substantive[0]!)
    .map(sanitizeTableCell)
    .slice(0, MAX_COMPARISON_COLUMNS)
  if (headers.filter((c) => c.trim()).length < 2) return null
  const rows: string[][] = []
  for (const line of substantive.slice(1)) {
    if (isMarkdownTableDividerLine(line)) continue
    const cells = splitMarkdownTableRow(line).map(sanitizeTableCell)
    while (cells.length < headers.length) cells.push('')
    rows.push(cells.slice(0, headers.length))
  }
  return rows.length >= 2 ? { headers, rows } : null
}

function parseOverviewBodyToRows(
  bodyLines: string[],
): { headers: string[]; rows: string[][] } | null {
  const headers = overviewHeadersFromBody(bodyLines)
  if (headers) {
    const rows = parseOverviewFieldRows(bodyLines, headers)
    if (rows) return { headers, rows }
  }
  return parseCollapsedOverviewBody(bodyLines)
}

function parseSectionToTable(
  headingLine: string,
  bodyLines: string[],
  intent?: string,
): { headers: string[]; rows: string[][] } | null {
  const resolvedIntent = intent ?? inferSectionIntent(headingLine, bodyLines)
  if (resolvedIntent === 'explicit_grid') return parseExplicitHeaderGrid(bodyLines)
  if (resolvedIntent === 'comparison') {
    return parseComparisonBodyToRows(bodyLines, inferColumnsFromHeading(headingLine))
  }
  if (resolvedIntent === 'overview') {
    const overview = parseOverviewBodyToRows(bodyLines)
    if (overview) return overview
    return parseComparisonBodyToRows(bodyLines, inferColumnsFromHeading(headingLine))
  }
  const comparison = parseComparisonBodyToRows(bodyLines, inferColumnsFromHeading(headingLine))
  if (comparison) return comparison
  return parseOverviewBodyToRows(bodyLines)
}

function shouldAttemptPseudoNormalize(
  _headingLine: string,
  bodyLines: string[],
  intent: string,
): boolean {
  if (intent === 'comparison') return true
  if (intent === 'overview') {
    return countPseudoTableSignals(bodyLines) >= 1 || overviewHeadersFromBody(bodyLines) !== null
  }
  if (intent === 'explicit_grid') return true
  return countPseudoTableSignals(bodyLines) >= 2
}

const ENTITY_PREFIX_RE = /^[A-Za-z0-9 .+-]+:\s*/

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

function tryNormalizeParagraphToTable(paraLines: string[]): string[] | null {
  if (!paraLines.length || sectionHasMarkdownTable(paraLines)) return null
  const parsed = parseCollapsedRecordRows(paraLines)
  if (parsed) return renderMarkdownTable(parsed.headers, parsed.rows)
  return null
}

function normalizeUnheadedCollapsedParagraphs(text: string): string {
  if (!text?.trim()) return text || ''
  const lines = text.split('\n')
  const out: string[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]!
    if (HEADING_LINE_RE.test(line)) {
      out.push(line)
      i++
      continue
    }
    const chunk: string[] = []
    while (i < lines.length && !HEADING_LINE_RE.test(lines[i]!)) {
      chunk.push(lines[i]!)
      i++
    }
    let para: string[] = []
    for (const ln of chunk) {
      if (!ln.trim()) {
        const table = tryNormalizeParagraphToTable(para)
        if (table) out.push(...table)
        else if (para.length) out.push(...para)
        out.push(ln)
        para = []
      } else {
        para.push(ln)
      }
    }
    const table = tryNormalizeParagraphToTable(para)
    if (table) out.push(...table)
    else if (para.length) out.push(...para)
  }
  return out.join('\n')
}

function needsPseudoTableNormalize(text: string): boolean {
  if (text.includes('|')) return true
  if (text.includes('____') || /_{4,}/.test(text)) return true
  if (text.includes('**') && /^\*\*[^*]+\*\*/m.test(text)) return true
  if (/\b(versus|vs\.?|vergelijk|comparison|overzicht|auxiliary)\b/i.test(text)) return true
  if (/[—–-]{4,}/.test(text)) return true
  const fieldRepeatMatches = text.match(FIELD_REPEAT_GATE_RE) ?? []
  return fieldRepeatMatches.length >= 2
}

function normalizePseudoTablesToMarkdown(text: string): string {
  if (!text?.trim()) return text || ''
  text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  if (!needsPseudoTableNormalize(text)) {
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

    const intent = inferSectionIntent(heading, bodyLines)
    if (!shouldAttemptPseudoNormalize(heading, bodyLines, intent)) {
      out.push(heading)
      out.push(...bodyLines)
      continue
    }

    const parsed = parseSectionToTable(heading, bodyLines, intent)
    if (parsed) {
      out.push(heading)
      out.push(...renderMarkdownTable(parsed.headers, parsed.rows))
      continue
    }

    out.push(heading)
    out.push(...bodyLines)
  }

  return normalizeUnheadedCollapsedParagraphs(out.join('\n'))
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
