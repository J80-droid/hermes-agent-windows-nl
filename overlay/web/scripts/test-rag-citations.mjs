/** Minimale check voor wrapBronCitationsForDisplay (zonder vitest). */
const BRON_CITATION = /(?<!`)(\[Bron:\s*([^\]]+?)\s*\])(?!`)/g;

function wrapBronCitationsForDisplay(text) {
  if (!text) return text;
  return text.replace(BRON_CITATION, "`$1`");
}

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL:", msg);
    process.exit(1);
  }
}

const raw = "Feit [Bron: brief.pdf] en `al [Bron: x]` ok.";
const out = wrapBronCitationsForDisplay(raw);
assert(out.includes("`[Bron: brief.pdf]`"), "backticks toegevoegd");
assert(out.includes("`al [Bron: x]`"), "bestaande backticks intact");
console.log("OK web/scripts/test-rag-citations.mjs");
