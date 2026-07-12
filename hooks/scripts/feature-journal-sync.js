#!/usr/bin/env node
// EDS — Stop hook (FDE companion to harvest-debt.js).
// If a project has an active FDE campaign (.eds/features/feature_catalog.json
// exists), appends this session's new/changed catalog entries to
// feature_journal.md, and increments each candidate-status entry's
// sessions_open counter — flagging entries open too long as pruning
// candidates. No-op if no campaign exists (most sessions).

const fs = require('fs');
const path = require('path');

const MAX_CANDIDATE_SESSIONS = 5;

function findFeaturesDir(startDir) {
  let dir = startDir;
  for (;;) {
    const candidate = path.join(dir, '.eds', 'features');
    if (fs.existsSync(path.join(candidate, 'feature_catalog.json'))) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function main() {
  const featuresDir = findFeaturesDir(process.cwd());
  if (!featuresDir) return;

  const catalogPath = path.join(featuresDir, 'feature_catalog.json');
  const snapshotPath = path.join(featuresDir, '.catalog-snapshot.json');
  const journalPath = path.join(featuresDir, 'feature_journal.md');

  let catalog;
  try {
    catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
  } catch (e) {
    return;
  }

  let prevByName = {};
  if (fs.existsSync(snapshotPath)) {
    try {
      const prev = JSON.parse(fs.readFileSync(snapshotPath, 'utf8'));
      prevByName = Object.fromEntries(prev.map((e) => [e.name, e]));
    } catch (e) {
      // treat as first run
    }
  }

  const journalLines = [];
  for (const entry of catalog) {
    const prev = prevByName[entry.name];
    if (!prev) {
      journalLines.push(`- [new] \`${entry.name}\` (${entry.family || 'unknown family'}) — status: ${entry.status}, hypothesis: ${entry.hypothesis_id || 'n/a'}`);
    } else if (prev.status !== entry.status) {
      journalLines.push(`- [status change] \`${entry.name}\`: ${prev.status} → ${entry.status}`);
    }

    if (entry.status === 'candidate') {
      entry.sessions_open = (entry.sessions_open || 0) + 1;
      if (entry.sessions_open >= MAX_CANDIDATE_SESSIONS) {
        journalLines.push(`- [stale] \`${entry.name}\` candidate for ${entry.sessions_open} sessions — recommend pruning or promoting`);
      }
    }
  }

  if (journalLines.length > 0) {
    const dateStamp = new Date().toISOString().slice(0, 10);
    const needsHeader = !fs.existsSync(journalPath);
    const header = needsHeader ? '# Feature journal\n\nAppend-only. Grep on demand — never bulk-load into context.\n' : '';
    fs.appendFileSync(journalPath, `${header}\n## ${dateStamp}\n\n${journalLines.join('\n')}\n`);
  }

  fs.writeFileSync(catalogPath, JSON.stringify(catalog, null, 2));
  fs.writeFileSync(snapshotPath, JSON.stringify(catalog, null, 2));
}

try {
  main();
} catch (e) {
  // Silent fail — journal sync is best-effort, must never block Stop.
}
