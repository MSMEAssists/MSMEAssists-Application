/**
 * Builds a downloadable PDF from the authenticated user's scheme report.
 * Uses the same orchestration + profile payload already loaded on /decision.
 * No backend PDF endpoint exists in this project; this encodes that live data
 * into a standard PDF file the browser can save.
 */

function pdfEscape(text) {
  return String(text ?? "")
    .replace(/\\/g, "\\\\")
    .replace(/\(/g, "\\(")
    .replace(/\)/g, "\\)")
    .replace(/\r/g, "")
    .replace(/\u20b9/g, "Rs.")
    .replace(/[^\t\n\x20-\x7E]/g, "-");
}

function wrapLine(text, maxChars) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  const lines = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > maxChars && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) lines.push(current);
  return lines.length ? lines : [""];
}

function buildPdf(pages) {
  const objects = [];
  const add = (body) => {
    objects.push(body);
    return objects.length;
  };

  const fontId = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
  const fontBoldId = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>");

  const pageIds = [];
  const contentIds = [];

  pages.forEach((contentStream) => {
    const stream = contentStream;
    const contentId = add(
      `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`
    );
    contentIds.push(contentId);
    pageIds.push(null);
  });

  const pagesIdPlaceholder = objects.length + 1 + pageIds.length;

  pages.forEach((_, idx) => {
    const pageId = add(
      `<< /Type /Page /Parent ${pagesIdPlaceholder} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 ${fontId} 0 R /F2 ${fontBoldId} 0 R >> >> /Contents ${contentIds[idx]} 0 R >>`
    );
    pageIds[idx] = pageId;
  });

  const kids = pageIds.map((id) => `${id} 0 R`).join(" ");
  const pagesId = add(`<< /Type /Pages /Kids [ ${kids} ] /Count ${pageIds.length} >>`);
  if (pagesId !== pagesIdPlaceholder) {
    throw new Error("PDF page tree could not be assembled.");
  }
  const catalogId = add(`<< /Type /Catalog /Pages ${pagesId} 0 R >>`);

  let offset = 0;
  const header = "%PDF-1.4\n";
  offset += header.length;
  const xref = [0];
  const bodyParts = [];
  objects.forEach((obj, i) => {
    xref.push(offset);
    const chunk = `${i + 1} 0 obj\n${obj}\nendobj\n`;
    bodyParts.push(chunk);
    offset += chunk.length;
  });

  const xrefStart = offset;
  let xrefTable = `xref\n0 ${objects.length + 1}\n`;
  xrefTable += "0000000000 65535 f \n";
  for (let i = 1; i < xref.length; i += 1) {
    xrefTable += `${String(xref[i]).padStart(10, "0")} 00000 n \n`;
  }
  const trailer = `trailer\n<< /Size ${objects.length + 1} /Root ${catalogId} 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;
  return header + bodyParts.join("") + xrefTable + trailer;
}

function textOps(items) {
  const ops = ["BT"];
  items.forEach((item) => {
    const font = item.bold ? "F2" : "F1";
    const size = item.size || 11;
    ops.push(`/${font} ${size} Tf`);
    ops.push(`${item.x} ${item.y} Td`);
    ops.push(`(${pdfEscape(item.text)}) Tj`);
    ops.push(`${-item.x} ${-item.y} Td`);
  });
  ops.push("ET");
  return ops.join("\n");
}

function collectReportLines(report) {
  const { profileFields = [], schemes = [], generatedAt = "", nextSteps = [] } = report || {};
  const lines = [];
  const push = (text, opts = {}) => lines.push({ text, ...opts });

  push("MSMEAssist", { bold: true, size: 16 });
  push("Your Personalized Scheme Report", { bold: true, size: 14 });
  push("Recommended government schemes, eligibility findings, and next steps.");
  if (generatedAt) push(`Report date: ${generatedAt}`);
  push("");
  push("This report is a decision aid. It does not guarantee scheme approval or funding.");
  push("");

  push("Business Profile Summary", { bold: true, size: 13 });
  if (!profileFields.length) {
    push("No saved business profile details were available.");
  } else {
    profileFields.forEach((field) => push(`${field.label}: ${field.value}`));
  }
  push("");

  push("Recommended Government Schemes", { bold: true, size: 13 });
  if (!schemes.length) {
    push("No ranked scheme recommendations were available for this profile.");
  } else {
    schemes.forEach((scheme) => {
      push("");
      push(`${scheme.rank}. ${scheme.title}`, { bold: true, size: 12 });
      if (scheme.organization) push(`Organisation: ${scheme.organization}`);
      if (scheme.eligibilityLabel) push(`Eligibility finding: ${scheme.eligibilityLabel}`);
      if (scheme.matchLabel) push(scheme.matchLabel);
      if (scheme.why) wrapLine(scheme.why, 92).forEach((l) => push(l));
      if (scheme.benefits?.length) {
        push("Benefits:", { bold: true });
        scheme.benefits.forEach((b) => wrapLine(`- ${b}`, 90).forEach((l) => push(l)));
      }
      if (scheme.conditions?.length) {
        push("Eligibility conditions to review:", { bold: true });
        scheme.conditions.forEach((c) => wrapLine(`- ${c}`, 90).forEach((l) => push(l)));
      }
      if (scheme.documents?.length) {
        push("Required documents:", { bold: true });
        scheme.documents.forEach((d) => wrapLine(`- ${d}`, 90).forEach((l) => push(l)));
      }
      if (scheme.guidelinesUrl) push(`Official guidelines: ${scheme.guidelinesUrl}`);
      if (scheme.applyUrl) push(`Application portal: ${scheme.applyUrl}`);
    });
  }

  push("");
  push("Your Next Steps", { bold: true, size: 13 });
  nextSteps.forEach((step, idx) => {
    wrapLine(`${idx + 1}. ${step.title}: ${step.detail}`, 92).forEach((l) => push(l));
  });

  push("");
  push("Always verify conditions on the official government portal before applying.");
  return lines;
}

function paginate(lines) {
  const pages = [];
  const left = 48;
  const top = 800;
  const lineHeight = 14;
  const bottom = 48;
  let y = top;
  let items = [];

  const flush = () => {
    if (items.length) pages.push(textOps(items));
    items = [];
    y = top;
  };

  lines.forEach((line) => {
    const size = line.size || 11;
    const needed = lineHeight + (size > 12 ? 4 : 0);
    if (y - needed < bottom) flush();
    items.push({
      text: line.text || " ",
      x: left,
      y,
      size,
      bold: Boolean(line.bold),
    });
    y -= needed;
  });
  flush();
  return pages.length ? pages : [textOps([{ text: "Report unavailable.", x: left, y: top, size: 12 }])];
}

export function generatePersonalizedSchemePdfString(report) {
  if (!report) {
    throw new Error("Report data is not available yet.");
  }
  return buildPdf(paginate(collectReportLines(report)));
}

export function downloadPersonalizedSchemePdf(report) {
  const pdf = generatePersonalizedSchemePdfString(report);
  const blob = new Blob([pdf], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const safeName = (report.businessName || "MSMEAssist")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);
  link.href = url;
  link.download = `${safeName || "MSMEAssist"}-Scheme-Report.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
