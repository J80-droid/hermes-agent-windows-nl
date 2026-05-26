import { useMemo, type ReactNode } from "react";
import { useAssistantDisplay } from "../contexts/useAssistantDisplay";
import { wrapBronCitationsForDisplay } from "../lib/ragCitations";
import {
  normalizeAssistantMarkdown,
} from "../lib/institutionalMarkdown";
import {
  webHeadingClass,
  webLabelClass,
  webTableCellClass,
  webTableHeaderClass,
} from "../lib/institutionalWebPalette";

/**
 * Lightweight markdown renderer for LLM output.
 * Handles: code blocks, inline code, bold, italic, headers, links, lists, horizontal rules.
 * NOT a full CommonMark parser — optimized for typical assistant message patterns.
 *
 * `streaming` renders a blinking caret at the tail of the last block so it
 * appears to hug the final character instead of wrapping onto a new line
 * after a block element (paragraph/list/code/…).
 */
export function Markdown({
  content,
  highlightTerms,
  streaming,
  assistantPalette,
}: {
  content: string;
  highlightTerms?: string[];
  streaming?: boolean;
  /** Overrides live gateway config; omit to use display.assistant_palette from API. */
  assistantPalette?: string;
}) {
  const { assistant_palette: configPalette } = useAssistantDisplay();
  const palette = assistantPalette ?? configPalette;
  const displayContent = useMemo(
    () => wrapBronCitationsForDisplay(normalizeAssistantMarkdown(content)),
    [content],
  );
  const blocks = useMemo(() => parseBlocks(displayContent), [displayContent]);
  const units = useMemo(() => toRenderUnits(blocks), [blocks]);
  const caret = streaming ? <StreamingCaret /> : null;

  return (
    <div className="text-sm text-foreground leading-relaxed space-y-1 [&_h1]:mb-0 [&_h2]:mb-0 [&_h3]:mb-0 [&_h4]:mb-0 [&_table]:mt-0 [&_ul]:mt-0 [&_ol]:mt-0">
      {units.map((unit, i) => {
        const isLast = i === units.length - 1;
        if (unit.kind === "tight") {
          return (
            <div key={i} className="space-y-0">
              {unit.blocks.map((block, j) => (
                <Block
                  key={j}
                  block={block}
                  highlightTerms={highlightTerms}
                  assistantPalette={palette}
                  caret={caret && isLast && j === unit.blocks.length - 1 ? caret : null}
                />
              ))}
            </div>
          );
        }
        return (
          <Block
            key={i}
            block={unit.block}
            highlightTerms={highlightTerms}
            assistantPalette={palette}
            caret={caret && isLast ? caret : null}
          />
        );
      })}
      {units.length === 0 && caret}
    </div>
  );
}

function StreamingCaret() {
  return (
    <span
      aria-hidden
      className="inline-block w-[0.5em] h-[1em] ml-0.5 align-[-0.15em] bg-foreground/50 animate-pulse"
    />
  );
}

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type BlockNode =
  | { type: "code"; lang: string; content: string }
  | { type: "heading"; level: number; content: string }
  | { type: "hr" }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "label"; label: string; content: string }
  | { type: "paragraph"; content: string };

type RenderUnit =
  | { kind: "tight"; blocks: BlockNode[] }
  | { kind: "loose"; block: BlockNode };

function toRenderUnits(blocks: BlockNode[]): RenderUnit[] {
  const units: RenderUnit[] = [];
  let i = 0;
  while (i < blocks.length) {
    const block = blocks[i]!;
    const next = blocks[i + 1];
    if (
      block.type === "heading" &&
      next &&
      (next.type === "table" ||
        next.type === "list" ||
        next.type === "paragraph" ||
        next.type === "label")
    ) {
      units.push({ kind: "tight", blocks: [block, next] });
      i += 2;
      continue;
    }
    units.push({ kind: "loose", block });
    i += 1;
  }
  return units;
}

/* ------------------------------------------------------------------ */
/*  Block parser                                                       */
/* ------------------------------------------------------------------ */

function parseBlocks(text: string): BlockNode[] {
  const lines = text.split("\n");
  const blocks: BlockNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    const fenceMatch = line.match(/^```(\w*)/);
    if (fenceMatch) {
      const lang = fenceMatch[1] || "";
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      blocks.push({ type: "code", lang, content: codeLines.join("\n") });
      continue;
    }

    // Heading
    const headingMatch = line.match(/^(#{1,4})\s+(.+)/);
    if (headingMatch) {
      blocks.push({
        type: "heading",
        level: headingMatch[1].length,
        content: headingMatch[2],
      });
      i++;
      continue;
    }

    // Horizontal rule
    if (/^[-*_]{3,}\s*$/.test(line)) {
      blocks.push({ type: "hr" });
      i++;
      continue;
    }

    // Unordered list
    if (/^[-*+]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*+]\s/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*+]\s/, ""));
        i++;
      }
      blocks.push({ type: "list", ordered: false, items });
      continue;
    }

    // Markdown table
    if (
      line.includes("|") &&
      i + 1 < lines.length &&
      /^\s*\|?[\s|:-]+\|?\s*$/.test(lines[i + 1]!)
    ) {
      const splitRow = (row: string) =>
        row
          .trim()
          .replace(/^\|/, "")
          .replace(/\|$/, "")
          .split("|")
          .map((c) => c.trim());
      const headers = splitRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].includes("|")) {
        if (!/^[\s|:-]+$/.test(lines[i])) {
          rows.push(splitRow(lines[i]));
        }
        i++;
      }
      blocks.push({ type: "table", headers, rows });
      continue;
    }

    // Label column: **Label:** then body lines
    const labelMatch = line.match(/^\*\*(.+?):\*\*\s*$/);
    if (labelMatch && i + 1 < lines.length && lines[i + 1].trim()) {
      const bodyLines: string[] = [];
      let j = i + 1;
      while (
        j < lines.length &&
        lines[j].trim() &&
        !lines[j].match(/^#{1,6}\s/) &&
        !lines[j].match(/^\*\*(.+?):\*\*\s*$/)
      ) {
        bodyLines.push(lines[j]);
        j++;
      }
      if (bodyLines.length) {
        blocks.push({
          type: "label",
          label: labelMatch[1],
          content: bodyLines.join("\n"),
        });
        i = j;
        continue;
      }
    }

    // Ordered list
    if (/^\d+[.)]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+[.)]\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+[.)]\s/, ""));
        i++;
      }
      blocks.push({ type: "list", ordered: true, items });
      continue;
    }

    // Empty line
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Paragraph — collect consecutive non-empty, non-special lines
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !lines[i].match(/^```/) &&
      !lines[i].match(/^#{1,4}\s/) &&
      !lines[i].match(/^[-*+]\s/) &&
      !lines[i].match(/^\d+[.)]\s/) &&
      !lines[i].match(/^[-*_]{3,}\s*$/)
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      blocks.push({ type: "paragraph", content: paraLines.join("\n") });
    }
  }

  return blocks;
}

/* ------------------------------------------------------------------ */
/*  Block renderer                                                     */
/* ------------------------------------------------------------------ */

function Block({
  block,
  highlightTerms,
  assistantPalette,
  caret,
}: {
  block: BlockNode;
  highlightTerms?: string[];
  assistantPalette?: string;
  caret?: ReactNode;
}) {
  switch (block.type) {
    case "code":
      return (
        <pre className="bg-secondary/60 border border-border px-3 py-2.5 text-xs font-mono leading-relaxed overflow-x-auto">
          <code>
            {block.content}
            {caret}
          </code>
        </pre>
      );

    case "heading": {
      const Tag = `h${Math.min(block.level, 4)}` as "h1" | "h2" | "h3" | "h4";
      const sizes: Record<string, string> = {
        h1: "text-base font-bold",
        h2: "text-sm font-bold",
        h3: "text-sm font-semibold",
        h4: "text-sm font-medium",
      };
      return (
        <Tag className={`${sizes[Tag]} ${webHeadingClass(assistantPalette, block.level)}`}>
          <InlineContent text={block.content} highlightTerms={highlightTerms} />
          {caret}
        </Tag>
      );
    }

    case "table":
      return (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr>
                {block.headers.map((h, ci) => (
                  <th
                    key={ci}
                    className={`text-left font-bold pr-4 pb-1 ${webTableHeaderClass(assistantPalette, ci)}`}
                  >
                    <InlineContent text={h} highlightTerms={highlightTerms} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, ri) => (
                <tr key={ri} className="border-t border-border/40">
                  {row.map((cell, ci) => (
                    <td key={ci} className={`pr-4 py-1 align-top ${webTableCellClass(assistantPalette, ci)}`}>
                      <InlineContent text={cell} highlightTerms={highlightTerms} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {caret}
        </div>
      );

    case "label":
      return (
        <div className="flex flex-col gap-0.5">
          <div className={webLabelClass(assistantPalette)}>{block.label}:</div>
          <div className="min-w-0">
            <InlineContent text={block.content} highlightTerms={highlightTerms} />
            {caret}
          </div>
        </div>
      );

    case "hr":
      return (
        <>
          <hr className="border-border" />
          {caret}
        </>
      );

    case "list": {
      const Tag = block.ordered ? "ol" : "ul";
      const last = block.items.length - 1;
      return (
        <Tag
          className={`space-y-1 ${block.ordered ? "list-decimal" : "list-[circle]"} pl-5 text-sm marker:text-muted-foreground`}
        >
          {block.items.map((item, i) => (
            <li key={i}>
              <InlineContent text={item} highlightTerms={highlightTerms} />
              {i === last ? caret : null}
            </li>
          ))}
        </Tag>
      );
    }

    case "paragraph":
      return (
        <p>
          <InlineContent text={block.content} highlightTerms={highlightTerms} />
          {caret}
        </p>
      );
  }
}

/* ------------------------------------------------------------------ */
/*  Inline parser + renderer                                           */
/* ------------------------------------------------------------------ */

type InlineNode =
  | { type: "text"; content: string }
  | { type: "code"; content: string }
  | { type: "bold"; content: string }
  | { type: "italic"; content: string }
  | { type: "link"; text: string; href: string }
  | { type: "br" };

function parseInline(text: string): InlineNode[] {
  const nodes: InlineNode[] = [];
  // Pattern priority: code > link > bold > italic > bare URL > line break
  const pattern =
    /(`[^`]+`)|(\[([^\]]+)\]\(([^)]+)\))|(\*\*([^*]+)\*\*)|(\*([^*]+)\*)|(\bhttps?:\/\/[^\s<>)\]]+)|(\n)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push({ type: "text", content: text.slice(lastIndex, match.index) });
    }

    if (match[1]) {
      // Inline code
      nodes.push({ type: "code", content: match[1].slice(1, -1) });
    } else if (match[2]) {
      // [text](url) link
      nodes.push({ type: "link", text: match[3], href: match[4] });
    } else if (match[5]) {
      // **bold**
      nodes.push({ type: "bold", content: match[6] });
    } else if (match[7]) {
      // *italic*
      nodes.push({ type: "italic", content: match[8] });
    } else if (match[9]) {
      // Bare URL
      nodes.push({ type: "link", text: match[9], href: match[9] });
    } else if (match[10]) {
      // Line break within paragraph
      nodes.push({ type: "br" });
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    nodes.push({ type: "text", content: text.slice(lastIndex) });
  }

  return nodes;
}

function InlineContent({
  text,
  highlightTerms,
}: {
  text: string;
  highlightTerms?: string[];
}) {
  const nodes = useMemo(() => parseInline(text), [text]);

  return (
    <>
      {nodes.map((node, i) => {
        switch (node.type) {
          case "text":
            return (
              <HighlightedText
                key={i}
                text={node.content}
                terms={highlightTerms}
              />
            );
          case "code":
            return (
              <code
                key={i}
                className="bg-secondary/60 px-1.5 py-0.5 text-xs font-mono text-primary/90"
              >
                {node.content}
              </code>
            );
          case "bold":
            return (
              <strong key={i} className="font-semibold">
                <HighlightedText text={node.content} terms={highlightTerms} />
              </strong>
            );
          case "italic":
            return (
              <em key={i}>
                <HighlightedText text={node.content} terms={highlightTerms} />
              </em>
            );
          case "link": {
            // Security: only render http(s)/mailto links. Other schemes
            // (javascript:, data:, vbscript:) are dropped to plain text so a
            // crafted link in agent/message content can't execute on click.
            const href = node.href.trim();
            if (!/^(https?:|mailto:)/i.test(href)) {
              return (
                <HighlightedText
                  key={i}
                  text={node.text}
                  terms={highlightTerms}
                />
              );
            }
            return (
              <a
                key={i}
                href={href}
                target="_blank"
                rel="noreferrer"
                className="text-primary underline underline-offset-2 decoration-primary/30 hover:decoration-primary/60 transition-colors"
              >
                {node.text}
              </a>
            );
          }
          case "br":
            return <br key={i} />;
        }
      })}
    </>
  );
}

/** Highlight search terms within a plain text string. */
function HighlightedText({ text, terms }: { text: string; terms?: string[] }) {
  if (!terms || terms.length === 0) return <>{text}</>;

  // Build a regex that matches any of the search terms (case-insensitive)
  const escaped = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const regex = new RegExp(`(${escaped.join("|")})`, "gi");
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-warning/30 text-warning px-0.5">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}
