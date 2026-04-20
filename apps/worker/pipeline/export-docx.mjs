/**
 * export-docx.mjs — Converts Research Markdown to DOCX
 *
 * Usage: node ecomtorials/export-docx.mjs <input.md> [output.docx]
 * If no output path given, replaces .md with .docx
 *
 * Parses markdown headings, bullet points, bold/italic, and tables
 * into a styled Word document with German locale.
 */

import { readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import {
  Document, Packer, Paragraph, TextRun, HeadingLevel,
  AlignmentType, BorderStyle, Table, TableRow, TableCell,
  WidthType, ShadingType,
} from "docx";

const inputPath = process.argv[2];
if (!inputPath) {
  console.error("Usage: node export-docx.mjs <input.md> [output.docx]");
  process.exit(1);
}

const outputPath = process.argv[3] || inputPath.replace(/\.md$/, ".docx");
const md = readFileSync(resolve(inputPath), "utf-8");

// Parse markdown into document sections
const lines = md.split("\n");
const children = [];

function parseInlineFormatting(text) {
  const runs = [];
  // Split by bold (**text**) and italic (*text*) markers
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]*\])/g);
  for (const part of parts) {
    if (!part) continue;
    if (part.startsWith("**") && part.endsWith("**")) {
      runs.push(new TextRun({ text: part.slice(2, -2), bold: true }));
    } else if (part.startsWith("*") && part.endsWith("*")) {
      runs.push(new TextRun({ text: part.slice(1, -1), italics: true }));
    } else if (part.startsWith("[") && part.endsWith("]")) {
      // Tags like [nicht verifiziert], [Quelle], [?]
      runs.push(new TextRun({ text: part, color: "666666", italics: true }));
    } else {
      runs.push(new TextRun({ text: part }));
    }
  }
  return runs;
}

function parseTableBlock(tableLines) {
  const rows = tableLines
    .filter(l => !l.match(/^\|[\s-:|]+\|$/)) // skip separator rows
    .map(l => l.split("|").slice(1, -1).map(c => c.trim()));

  if (rows.length === 0) return [];

  const tableRows = rows.map((cells, rowIdx) =>
    new TableRow({
      children: cells.map(cell =>
        new TableCell({
          children: [new Paragraph({
            children: parseInlineFormatting(cell),
            spacing: { before: 40, after: 40 },
          })],
          width: { size: Math.floor(9000 / cells.length), type: WidthType.DXA },
          shading: rowIdx === 0
            ? { type: ShadingType.SOLID, color: "E8E8E8" }
            : undefined,
        })
      ),
    })
  );

  return [new Table({
    rows: tableRows,
    width: { size: 9000, type: WidthType.DXA },
  })];
}

let i = 0;
while (i < lines.length) {
  const line = lines[i];

  // Tables
  if (line.startsWith("|")) {
    const tableLines = [];
    while (i < lines.length && lines[i].startsWith("|")) {
      tableLines.push(lines[i]);
      i++;
    }
    children.push(...parseTableBlock(tableLines));
    continue;
  }

  // Code blocks — render as indented plain text
  if (line.startsWith("```")) {
    i++; // skip opening fence
    while (i < lines.length && !lines[i].startsWith("```")) {
      children.push(new Paragraph({
        children: [new TextRun({ text: lines[i], font: "Consolas", size: 18 })],
        indent: { left: 720 },
        spacing: { before: 40, after: 40 },
      }));
      i++;
    }
    i++; // skip closing fence
    continue;
  }

  // Headings
  if (line.startsWith("# ")) {
    children.push(new Paragraph({
      children: [new TextRun({ text: line.replace(/^# /, ""), bold: true, size: 32 })],
      heading: HeadingLevel.HEADING_1,
      spacing: { before: 360, after: 120 },
    }));
    i++;
    continue;
  }
  if (line.startsWith("## ")) {
    children.push(new Paragraph({
      children: [new TextRun({ text: line.replace(/^## /, ""), bold: true, size: 28 })],
      heading: HeadingLevel.HEADING_2,
      spacing: { before: 280, after: 100 },
    }));
    i++;
    continue;
  }
  if (line.startsWith("### ")) {
    children.push(new Paragraph({
      children: [new TextRun({ text: line.replace(/^### /, ""), bold: true, size: 24 })],
      heading: HeadingLevel.HEADING_3,
      spacing: { before: 200, after: 80 },
    }));
    i++;
    continue;
  }

  // Horizontal rules
  if (line.match(/^---+$/)) {
    children.push(new Paragraph({
      children: [],
      border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" } },
      spacing: { before: 120, after: 120 },
    }));
    i++;
    continue;
  }

  // Bullet points (- or *)
  if (line.match(/^\s*[-*]\s/)) {
    const text = line.replace(/^\s*[-*]\s/, "").trim();
    const indent = line.match(/^(\s*)/)[1].length;
    children.push(new Paragraph({
      children: parseInlineFormatting(text),
      bullet: { level: Math.min(Math.floor(indent / 2), 3) },
      spacing: { before: 40, after: 40 },
    }));
    i++;
    continue;
  }

  // Empty lines
  if (line.trim() === "") {
    children.push(new Paragraph({ children: [], spacing: { before: 60, after: 60 } }));
    i++;
    continue;
  }

  // Regular paragraph
  children.push(new Paragraph({
    children: parseInlineFormatting(line),
    spacing: { before: 60, after: 60 },
  }));
  i++;
}

// Build document
const doc = new Document({
  sections: [{
    properties: {
      page: {
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    children,
  }],
  styles: {
    default: {
      document: {
        run: { font: "Calibri", size: 22 },
      },
    },
  },
});

const buffer = await Packer.toBuffer(doc);
writeFileSync(resolve(outputPath), buffer);
console.log(`DOCX created: ${resolve(outputPath)}`);
