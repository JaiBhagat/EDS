#!/usr/bin/env node
// EDS — Stop hook.
// Sweeps `eds: deferred — <reason>` markers out of files touched this
// session and appends new ones to .eds/debt-ledger.md, so a deliberate
// shortcut stays visible instead of silently becoming permanent.
// Read-only on source files; only ever appends to the ledger.

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

// Anchored: # must be at line start (with optional whitespace) — a real comment,
// not a marker pattern quoted inside a string literal or docstring.
const MARKER_RE = /^\s*#\s*eds:\s*deferred\s*(?:—|--|-)\s*(.+)/i;
const MAX_FALLBACK_FILES = 500;
const SOURCE_EXTS = new Set(['.py', '.ipynb', '.sql', '.md', '.R', '.r', '.js', '.ts']);

function findRepoRoot(startDir) {
  let dir = startDir;
  for (;;) {
    if (fs.existsSync(path.join(dir, '.git'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function gitChangedFiles(repoRoot) {
  const args = ['-C', repoRoot, 'status', '--porcelain'];
  const result = spawnSync('git', args, { encoding: 'utf8' });
  if (result.status !== 0 || !result.stdout) return null;
  return result.stdout
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      const entry = line.slice(3).trim();
      // Handle renamed files: "R  old -> new" — take the new path
      if (entry.includes(' -> ')) return entry.split(' -> ').pop();
      return entry;
    })
    .filter(Boolean)
    .map((f) => path.join(repoRoot, f));
}

function walkFallback(root) {
  const found = [];
  const stack = [root];
  while (stack.length && found.length < MAX_FALLBACK_FILES) {
    const dir = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch (e) {
      continue;
    }
    for (const entry of entries) {
      if (entry.name.startsWith('.') || entry.name === 'node_modules') continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        stack.push(full);
      } else if (SOURCE_EXTS.has(path.extname(entry.name))) {
        found.push(full);
      }
    }
  }
  return found;
}

// Paths excluded from harvest — test fixtures and build artifacts contain markers
// for testing purposes, not real deferred work.
const EXCLUDE_PATTERNS = [/\btests?\//, /\bbenchmarks\/fixtures\//, /\/__pycache__\//];

function extractMarkers(files) {
  const markers = [];
  for (const file of files) {
    // Skip test/fixture files — their markers are test data, not real debt
    if (EXCLUDE_PATTERNS.some((re) => re.test(file))) continue;
    let content;
    try {
      content = fs.readFileSync(file, 'utf8');
    } catch (e) {
      continue;
    }
    const lines = content.split(/\r?\n/);
    lines.forEach((line, idx) => {
      const m = line.match(MARKER_RE);
      if (!m) return;
      // Trim capture at end of reason — don't include trailing code
      const reason = m[1].split('\n')[0].trim();
      markers.push({ file, line: idx + 1, reason });
    });
  }
  return markers;
}

function main() {
  const cwd = process.cwd();
  const repoRoot = findRepoRoot(cwd);
  const files = (repoRoot && gitChangedFiles(repoRoot)) || walkFallback(cwd);
  const markers = extractMarkers(files.filter((f) => {
    try {
      return fs.statSync(f).isFile();
    } catch (e) {
      return false;
    }
  }));

  if (markers.length === 0) return;

  const ledgerDir = path.join(repoRoot || cwd, '.eds');
  const ledgerPath = path.join(ledgerDir, 'debt-ledger.md');
  fs.mkdirSync(ledgerDir, { recursive: true });

  let existing = '';
  const ledgerExisted = fs.existsSync(ledgerPath);
  if (ledgerExisted) {
    existing = fs.readFileSync(ledgerPath, 'utf8');
  } else {
    existing = '# EDS debt ledger\n\nHarvested `eds: deferred` markers — run `/eds-debt` to review, or clear an entry once addressed.\n';
    fs.writeFileSync(ledgerPath, existing);
  }

  const dateStamp = new Date().toISOString().slice(0, 10);
  const newLines = [];
  for (const marker of markers) {
    const entryKey = `${path.relative(repoRoot || cwd, marker.file)}:${marker.line}`;
    if (existing.includes(entryKey)) continue; // already harvested
    newLines.push(`- \`${entryKey}\` — ${marker.reason}`);
  }

  if (newLines.length === 0) return;

  const appended = `\n## ${dateStamp}\n\n${newLines.join('\n')}\n`;
  fs.appendFileSync(ledgerPath, existing.endsWith('\n') ? appended : `\n${appended}`);
}

try {
  main();
} catch (e) {
  // Silent fail — debt harvesting is best-effort, must never block Stop.
}
