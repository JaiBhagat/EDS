#!/usr/bin/env node
// EDS — debt-ledger -> instinct pipeline (ECC continuous-learning-v2
// pattern). Clusters recurring deferral reasons in .eds/debt-ledger.md by
// shared keyword, not embeddings/ML — a keyword histogram is the rung-6
// answer to "which deferrals keep recurring," and a repeated deferral is
// exactly the kind of pattern that's cheap to spot this way.
//
// Usage:
//   node scripts/evolve-cluster.js [ledger-path] [--min-count N] [--write]
// Default ledger path: .eds/debt-ledger.md under cwd (searched upward).

const fs = require('fs');
const path = require('path');

const STOPWORDS = new Set([
  'the', 'a', 'an', 'is', 'to', 'of', 'for', 'and', 'in', 'on', 'at', 'no', 'not',
  'this', 'that', 'it', 'be', 'with', 'as', 'from', 'or', 'has', 'have', 'was',
  'were', 'will', 'would', 'needs', 'need', 'needed', 'until', 'than', 'so',
  'because', 'but', 'if', 'still', 'yet', 'more', 'than', 'once', 'just', 'here',
]);

const ENTRY_RE = /^-\s*`([^`]+)`\s*—\s*(.+)$/;

function findLedgerPath(fromDir) {
  let dir = fromDir;
  for (;;) {
    const candidate = path.join(dir, '.eds', 'debt-ledger.md');
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function parseEntries(text) {
  const entries = [];
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(ENTRY_RE);
    if (m) entries.push({ ref: m[1], reason: m[2].trim() });
  }
  return entries;
}

function tokenize(reason) {
  return reason
    .toLowerCase()
    .replace(/[^a-z0-9_\s]/g, ' ')
    .split(/\s+/)
    .filter((t) => t.length > 2 && !STOPWORDS.has(t));
}

function cluster(entries, minCount) {
  const byToken = {};
  for (const entry of entries) {
    for (const token of new Set(tokenize(entry.reason))) {
      (byToken[token] = byToken[token] || []).push(entry);
    }
  }
  return Object.entries(byToken)
    .filter(([, es]) => es.length >= minCount)
    .sort((a, b) => b[1].length - a[1].length)
    .map(([token, es]) => ({ token, count: es.length, examples: es.slice(0, 3) }));
}

function formatReport(clusters, ledgerPath) {
  if (clusters.length === 0) {
    return `No recurring pattern found in ${ledgerPath} (nothing met the minimum count).`;
  }
  const lines = [`# Instinct candidates — clustered from ${ledgerPath}`, ''];
  for (const c of clusters) {
    lines.push(`## '${c.token}' — ${c.count} occurrence(s)`);
    for (const ex of c.examples) {
      lines.push(`- \`${ex.ref}\` — ${ex.reason}`);
    }
    lines.push(`Candidate action: recurring deferral around '${c.token}' — consider a dedicated check, skill section, or hook rule.`);
    lines.push('');
  }
  return lines.join('\n').trim() + '\n';
}

function main() {
  const argv = process.argv.slice(2);
  const positional = argv.filter((a) => !a.startsWith('--'));
  const minCountIdx = argv.indexOf('--min-count');
  const minCount = minCountIdx >= 0 ? parseInt(argv[minCountIdx + 1], 10) : 3;
  const write = argv.includes('--write');

  const ledgerPath = positional[0] || findLedgerPath(process.cwd());
  if (!ledgerPath || !fs.existsSync(ledgerPath)) {
    console.error('no .eds/debt-ledger.md found — nothing to cluster yet');
    process.exit(1);
  }

  const entries = parseEntries(fs.readFileSync(ledgerPath, 'utf8'));
  const clusters = cluster(entries, minCount);
  const report = formatReport(clusters, ledgerPath);
  console.log(report);

  if (write) {
    const outPath = path.join(path.dirname(ledgerPath), 'instinct-candidates.md');
    fs.writeFileSync(outPath, report);
    console.error(`written to ${outPath}`);
  }
}

main();
