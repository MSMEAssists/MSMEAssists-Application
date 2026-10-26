import React from "react";
import { FiExternalLink } from "react-icons/fi";

/**
 * Sanitizes URLs to prevent XSS (blocks javascript:, data:, vbscript: protocols).
 */
function sanitizeUrl(rawUrl) {
  if (!rawUrl || typeof rawUrl !== "string") return "#";
  const trimmed = rawUrl.trim();
  if (/^(https?:\/\/|\/|#|mailto:)/i.test(trimmed)) {
    return trimmed;
  }
  return "#";
}

/**
 * Parses inline markdown:
 * - Bold: **text**
 * - Italic: *text*
 * - Inline code: `text`
 * - Links: [label](url)
 * - Plain URLs: https://...
 */
function renderInline(text, keyPrefix = "inline") {
  if (!text) return null;

  // Regex tokens for inline parsing
  // Matches: `code`, **bold**, *italic*, [label](url), and standalone URLs
  const tokenRegex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\)|https?:\/\/[^\s<)]+)/g;

  const parts = [];
  let lastIndex = 0;
  let match;
  let idx = 0;

  while ((match = tokenRegex.exec(text)) !== null) {
    // Add text preceding the match
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const token = match[0];
    const itemKey = `${keyPrefix}-${idx++}`;

    if (token.startsWith("`") && token.endsWith("`") && token.length > 2) {
      parts.push(
        <code
          key={itemKey}
          className="rounded bg-warm-offwhite/90 border border-border px-1.5 py-0.5 font-mono text-[11px] text-charcoal font-semibold"
        >
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith("**") && token.endsWith("**") && token.length > 4) {
      parts.push(
        <strong key={itemKey} className="font-bold text-charcoal">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith("*") && token.endsWith("*") && token.length > 2) {
      parts.push(
        <em key={itemKey} className="italic text-slate-dark">
          {token.slice(1, -1)}
        </em>
      );
    } else if (token.startsWith("[") && token.includes("](") && token.endsWith(")")) {
      const splitIdx = token.indexOf("](");
      const label = token.slice(1, splitIdx);
      const rawUrl = token.slice(splitIdx + 2, -1);
      const safeUrl = sanitizeUrl(rawUrl);
      parts.push(
        <a
          key={itemKey}
          href={safeUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-burnt-orange hover:text-burnt-hover hover:underline inline-flex items-center gap-0.5"
        >
          <span>{label}</span>
          <FiExternalLink size={10} className="shrink-0" />
        </a>
      );
    } else if (token.startsWith("http://") || token.startsWith("https://")) {
      const safeUrl = sanitizeUrl(token);
      parts.push(
        <a
          key={itemKey}
          href={safeUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-burnt-orange hover:underline break-all inline-flex items-center gap-0.5 font-medium"
        >
          <span>{token}</span>
          <FiExternalLink size={10} className="shrink-0" />
        </a>
      );
    } else {
      parts.push(token);
    }

    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts;
}

/**
 * Checks if lines represent a markdown table
 */
function isTableBlock(lines) {
  if (lines.length < 2) return false;
  const first = lines[0].trim();
  const second = lines[1].trim();
  return (
    first.startsWith("|") &&
    first.endsWith("|") &&
    second.startsWith("|") &&
    second.includes("-")
  );
}

function parseTable(lines, blockKey) {
  const headerLine = lines[0].trim();
  const headers = headerLine
    .slice(1, -1)
    .split("|")
    .map((h) => h.trim());

  // skip separator line at index 1
  const bodyLines = lines.slice(2);

  return (
    <div key={blockKey} className="my-2.5 overflow-x-auto rounded-lg border border-border shadow-xs">
      <table className="min-w-full divide-y divide-border text-left text-xs">
        <thead className="bg-warm-offwhite/90">
          <tr>
            {headers.map((h, i) => (
              <th key={i} className="px-3 py-2 font-bold text-charcoal">
                {renderInline(h, `${blockKey}-th-${i}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border bg-white">
          {bodyLines.map((line, rIdx) => {
            const trimmed = line.trim();
            if (!trimmed.startsWith("|")) return null;
            const cells = trimmed
              .slice(1, -1)
              .split("|")
              .map((c) => c.trim());
            return (
              <tr key={rIdx} className="hover:bg-warm-offwhite/40">
                {cells.map((cell, cIdx) => (
                  <td key={cIdx} className="px-3 py-2 text-slate-dark">
                    {renderInline(cell, `${blockKey}-td-${rIdx}-${cIdx}`)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * SafeMarkdownRenderer
 *
 * Renders Markdown safely without dangerous HTML execution.
 * Handles headings (h1-h6), lists, tables, bold, italics, code, horizontal rules, and source links.
 * Guaranteed zero-infinite-loop invariant and memoized to avoid browser UI thread freezes.
 */
function SafeMarkdownRendererComponent({ content, className = "" }) {
  const elements = React.useMemo(() => {
    if (!content) return [];

    const rawLines = content.split(/\r?\n/);
    const parsed = [];
    let i = 0;
    let blockIdx = 0;

    while (i < rawLines.length) {
      const startI = i;
      const line = rawLines[i];
      const trimmed = line.trim();

      // 1. Skip completely empty lines
      if (!trimmed) {
        i++;
        continue;
      }

      // 2. Horizontal Rule: ---, ***, ___
      if (/^([-*_]){3,}$/.test(trimmed)) {
        parsed.push(<hr key={`hr-${blockIdx++}`} className="my-3 border-t border-border/80" />);
        i++;
        continue;
      }

      // 3. Headings: # through ######
      const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
      if (headingMatch) {
        const level = headingMatch[1].length;
        const headingText = headingMatch[2];
        const Tag = level === 1 ? "h2" : level === 2 ? "h3" : level === 3 ? "h4" : "h5";
        const headingClasses =
          level === 1
            ? "mt-4 mb-2 font-display text-base font-bold text-charcoal border-b border-border pb-1"
            : level === 2
            ? "mt-3.5 mb-1.5 font-display text-sm font-bold text-charcoal border-b border-border/60 pb-1"
            : level === 3
            ? "mt-3 mb-1.5 font-display text-xs font-bold uppercase tracking-wider text-charcoal"
            : "mt-2.5 mb-1 font-display text-xs font-bold text-charcoal";
        parsed.push(
          <Tag key={`h-${blockIdx++}`} className={headingClasses}>
            {renderInline(headingText, `h-${i}`)}
          </Tag>
        );
        i++;
        continue;
      }

      // 4. Table Block
      if (trimmed.startsWith("|") && i + 1 < rawLines.length && rawLines[i + 1].includes("|-")) {
        const tableLines = [];
        while (i < rawLines.length && rawLines[i].trim().startsWith("|")) {
          tableLines.push(rawLines[i]);
          i++;
        }
        parsed.push(parseTable(tableLines, `table-${blockIdx++}`));
        continue;
      }

      // 5. Code Block: ```
      if (trimmed.startsWith("```")) {
        const codeLines = [];
        i++;
        while (i < rawLines.length && !rawLines[i].trim().startsWith("```")) {
          codeLines.push(rawLines[i]);
          i++;
        }
        if (i < rawLines.length && rawLines[i].trim().startsWith("```")) {
          i++;
        }
        parsed.push(
          <pre
            key={`code-${blockIdx++}`}
            className="my-2 overflow-x-auto rounded-lg bg-charcoal p-3 font-mono text-[11px] text-white"
          >
            <code>{codeLines.join("\n")}</code>
          </pre>
        );
        continue;
      }

      // 6. Unordered list block (- or * or •)
      if (/^[-*•]\s+/.test(trimmed)) {
        const listItems = [];
        while (i < rawLines.length && /^[-*•]\s+/.test(rawLines[i].trim())) {
          listItems.push(rawLines[i].trim().replace(/^[-*•]\s+/, ""));
          i++;
        }
        parsed.push(
          <ul key={`ul-${blockIdx++}`} className="my-2 space-y-1 pl-4 list-disc marker:text-burnt-orange text-xs text-slate-dark">
            {listItems.map((item, lIdx) => (
              <li key={lIdx} className="leading-relaxed">
                {renderInline(item, `li-${blockIdx}-${lIdx}`)}
              </li>
            ))}
          </ul>
        );
        continue;
      }

      // 7. Ordered list block (1., 2., etc)
      if (/^\d+\.\s+/.test(trimmed)) {
        const listItems = [];
        while (i < rawLines.length && /^\d+\.\s+/.test(rawLines[i].trim())) {
          listItems.push(rawLines[i].trim().replace(/^\d+\.\s+/, ""));
          i++;
        }
        parsed.push(
          <ol key={`ol-${blockIdx++}`} className="my-2 space-y-1 pl-4 list-decimal marker:font-bold marker:text-burnt-orange text-xs text-slate-dark">
            {listItems.map((item, lIdx) => (
              <li key={lIdx} className="leading-relaxed">
                {renderInline(item, `oli-${blockIdx}-${lIdx}`)}
              </li>
            ))}
          </ol>
        );
        continue;
      }

      // 8. Blockquote: >
      if (trimmed.startsWith("> ")) {
        const quoteLines = [];
        while (i < rawLines.length && rawLines[i].trim().startsWith("> ")) {
          quoteLines.push(rawLines[i].trim().slice(2));
          i++;
        }
        parsed.push(
          <blockquote
            key={`quote-${blockIdx++}`}
            className="my-2 rounded-r-lg border-l-4 border-burnt-orange bg-warm-offwhite/60 p-2.5 text-xs italic text-slate-dark"
          >
            {quoteLines.map((ql, qIdx) => (
              <p key={qIdx}>{renderInline(ql, `q-${blockIdx}-${qIdx}`)}</p>
            ))}
          </blockquote>
        );
        continue;
      }

      // 9. Normal Paragraph: gather contiguous lines until empty line or special block token
      const paragraphLines = [];
      while (
        i < rawLines.length &&
        rawLines[i].trim() &&
        !/^(#{1,6})\s+/.test(rawLines[i].trim()) &&
        !rawLines[i].trim().startsWith("```") &&
        !/^[-*•]\s+/.test(rawLines[i].trim()) &&
        !/^\d+\.\s+/.test(rawLines[i].trim()) &&
        !rawLines[i].trim().startsWith("> ") &&
        !/^([-*_]){3,}$/.test(rawLines[i].trim()) &&
        !(rawLines[i].trim().startsWith("|") && i + 1 < rawLines.length && rawLines[i + 1].includes("|-"))
      ) {
        paragraphLines.push(rawLines[i].trim());
        i++;
      }

      if (paragraphLines.length > 0) {
        parsed.push(
          <p key={`p-${blockIdx++}`} className="my-1.5 text-xs leading-relaxed text-slate-dark">
            {paragraphLines.map((pl, pIdx) => (
              <React.Fragment key={pIdx}>
                {pIdx > 0 && " "}
                {renderInline(pl, `p-${blockIdx}-${pIdx}`)}
              </React.Fragment>
            ))}
          </p>
        );
      } else if (i < rawLines.length) {
        // Strict fallback to guarantee loop termination
        parsed.push(
          <p key={`p-fallback-${blockIdx++}`} className="my-1.5 text-xs leading-relaxed text-slate-dark">
            {renderInline(trimmed, `fallback-${i}`)}
          </p>
        );
        i++;
      }

      // Hard loop invariant: if i did not advance, force advance by 1
      if (i === startI) {
        i++;
      }
    }

    return parsed;
  }, [content]);

  if (!content) return null;
  return <div className={`space-y-1 break-words ${className}`}>{elements}</div>;
}

export default React.memo(SafeMarkdownRendererComponent);
