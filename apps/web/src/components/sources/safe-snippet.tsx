import { Fragment } from "react";

const ENTITIES: Record<string, string> = {
  "&amp;": "&",
  "&lt;": "<",
  "&gt;": ">",
  "&quot;": '"',
  "&#39;": "'",
  "&#x27;": "'",
  "&nbsp;": " ",
};

/** Decode the few entities the server uses when HTML-escaping. Result is only ever rendered as text. */
export function decodeEntities(text: string): string {
  return text.replace(/&(?:amp|lt|gt|quot|#39|#x27|nbsp);/g, (m) => ENTITIES[m] ?? m);
}

export interface SnippetPart {
  text: string;
  mark: boolean;
}

/**
 * Split a search snippet into text and highlighted parts.
 *
 * The server HTML-escapes everything except `<mark>…</mark>` around matches. Only those two tags are
 * honoured; any other markup that slips through (`<script>`, `<img onerror=…>`, nested tags, stray
 * closing tags) stays literal text. Output is rendered as React text nodes, never as HTML.
 */
export function parseSnippet(snippet: string): SnippetPart[] {
  const parts: SnippetPart[] = [];
  let mark = false;
  for (const token of snippet.split(/(<\/?mark>)/i)) {
    const lower = token.toLowerCase();
    if (lower === "<mark>") {
      mark = true;
    } else if (lower === "</mark>") {
      mark = false;
    } else if (token) {
      parts.push({ text: decodeEntities(token), mark });
    }
  }
  return parts;
}

export function SafeSnippet({ snippet, className }: { snippet: string; className?: string }) {
  return (
    <span className={className}>
      {parseSnippet(snippet).map((p, i) => (
        <Fragment key={i}>
          {p.mark ? (
            <mark className="rounded bg-yellow-200/70 px-0.5 dark:bg-yellow-500/40">{p.text}</mark>
          ) : (
            p.text
          )}
        </Fragment>
      ))}
    </span>
  );
}
