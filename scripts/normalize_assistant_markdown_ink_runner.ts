/** CLI: stdin markdown → stdout normalized (Ink TS normalizer). Used by pytest parity. */
import { readFileSync } from "node:fs";
import { normalizeAssistantMarkdown } from "../ui-tui/src/lib/institutionalMarkdownNormalize.ts";

const text = readFileSync(0, "utf8");
process.stdout.write(normalizeAssistantMarkdown(text));
