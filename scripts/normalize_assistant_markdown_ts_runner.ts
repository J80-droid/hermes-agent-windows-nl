/** CLI: stdin markdown → stdout normalized (Web TS normalizer). Used by pytest parity. */
import { normalizeAssistantMarkdown } from "../web/src/lib/institutionalMarkdown.ts";

const chunks: Buffer[] = [];
process.stdin.on("data", (c) => chunks.push(c as Buffer));
process.stdin.on("end", () => {
  const text = Buffer.concat(chunks).toString("utf8");
  process.stdout.write(normalizeAssistantMarkdown(text));
});
