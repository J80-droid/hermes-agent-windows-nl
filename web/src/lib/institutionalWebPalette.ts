/** Web assistant colours — mirror of config/palettes.yaml (demo + YAML palettes). */

export type WebAssistantPalette = {
  tableColumns: readonly string[]
  headings: readonly string[]
  label: string
}

const hex = (c: string) => `text-[${c}]`

const build = (
  tableColumns: string[],
  headings: string[],
  label: string,
): WebAssistantPalette => ({
  tableColumns: tableColumns.map(hex),
  headings: headings.map(hex),
  label: hex(label),
})

/** Built-in + YAML palette names (keep in sync with config/palettes.yaml). */
export const WEB_ASSISTANT_PALETTES: Record<string, WebAssistantPalette> = {
  demo: build(
    ['#66d9ef', '#a6e22e', '#f8f8f2', '#f92672'],
    ['#66d9ef', '#a6e22e', '#e6db74', '#ae81ff', '#cbd5e1', '#64748b'],
    '#f92672',
  ),
  monokai: build(
    ['#66d9ef', '#a6e22e', '#f8f8f2', '#f92672'],
    ['#66d9ef', '#a6e22e', '#e6db74', '#ae81ff', '#f8f8f2', '#64748b'],
    '#f92672',
  ),
  hermes: build(
    ['#FFD700', '#FFBF00', '#DAA520', '#FFF8DC'],
    ['#FFD700', '#FFBF00', '#DAA520', '#DAA520', '#DAA520', '#B8860B'],
    '#DAA520',
  ),
  neutral: build(
    ['#22d3ee', '#ffffff', '#a3a3a3', '#737373'],
    ['#ffffff', '#ffffff', '#a3a3a3', '#ffffff', '#d4d4d4', '#737373'],
    '#ffffff',
  ),
  dracula: build(
    ['#8be9fd', '#50fa7b', '#f8f8f2', '#ff79c6'],
    ['#8be9fd', '#50fa7b', '#ffb86c', '#bd93f9', '#f8f8f2', '#64748b'],
    '#ff79c6',
  ),
  tokyo: build(
    ['#00f0ff', '#39ff14', '#e0f7fa', '#ff007f'],
    ['#00f0ff', '#39ff14', '#fff000', '#b10dc9', '#e0f7fa', '#64748b'],
    '#ff007f',
  ),
  nordic: build(
    ['#88c0d0', '#8fbcbb', '#eceff4', '#d08770'],
    ['#88c0d0', '#8fbcbb', '#81a1c1', '#b48ead', '#eceff4', '#64748b'],
    '#f92672',
  ),
  pacific: build(
    ['#20b2aa', '#98fb98', '#e0eee0', '#f92672'],
    ['#20b2aa', '#98fb98', '#afeeee', '#dda0dd', '#e0eee0', '#64748b'],
    '#f92672',
  ),
}

export const resolveWebAssistantPalette = (name: string | undefined): WebAssistantPalette =>
  WEB_ASSISTANT_PALETTES[(name || 'demo').trim().toLowerCase()] ?? WEB_ASSISTANT_PALETTES.demo!

export const webTableHeaderClass = (palette: string | undefined, index: number): string => {
  const p = resolveWebAssistantPalette(palette)
  return p.tableColumns[index % p.tableColumns.length]!
}

export const webTableCellClass = webTableHeaderClass

export const webHeadingClass = (palette: string | undefined, level: number): string => {
  const p = resolveWebAssistantPalette(palette)
  const idx = Math.min(Math.max(level - 1, 0), p.headings.length - 1)
  return p.headings[idx]!
}

export const webLabelClass = (palette: string | undefined): string => {
  const p = resolveWebAssistantPalette(palette)
  return `${p.label} font-bold`
}
