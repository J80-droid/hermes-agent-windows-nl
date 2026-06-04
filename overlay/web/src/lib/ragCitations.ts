/** Zet niet-gebacktickte `[Bron: …]` tussen backticks voor inline-code chips. */
const BRON_CITATION = /(?<!`)(\[Bron:\s*([^\]]+?)\s*\])(?!`)/g;

export function wrapBronCitationsForDisplay(text: string): string {
  if (!text) return text;
  return text.replace(BRON_CITATION, "`$1`");
}
