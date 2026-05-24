/** CLI: stdin markdown → stdout normalized (Web TS normalizer). Used by pytest parity. */
import { readFileSync } from "node:fs";
import { normalizeAssistantMarkdown } from "../web/src/lib/institutionalMarkdown.ts";

const text = readFileSync(0, "utf8");
process.stdout.write(normalizeAssistantMarkdown(text));
