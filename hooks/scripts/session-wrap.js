#!/usr/bin/env node
// EDS — Stop hook: session wrap-up (H6).
// Checks state consistency and flags (never auto-fixes) issues.
// Runs AFTER harvest-debt and journal-sync in the Stop pipeline.

const fs = require('fs');
const path = require('path');

function findEdsRoot() {
  let dir = process.cwd();
  for (;;) {
    if (fs.existsSync(path.join(dir, '.eds'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function checkConsistency(edsRoot) {
  const issues = [];
  const edsDir = path.join(edsRoot, '.eds');

  // Check: Plan has in-progress stage with no resume info in progress.md
  const briefPath = path.join(edsDir, 'BRIEF.md');
  if (fs.existsSync(briefPath)) {
    const brief = fs.readFileSync(briefPath, 'utf8');
    const planIdx = brief.indexOf('## Plan');
    if (planIdx !== -1) {
      const planText = brief.slice(planIdx);
      if (/\bin-progress\b/i.test(planText)) {
        const progressPath = path.join(edsDir, 'progress.md');
        if (!fs.existsSync(progressPath)) {
          issues.push('Plan has in-progress stage but no progress.md — consider writing a handoff note');
        }
      }
    }
  }

  // Check: catalogs consistent (feature catalog exists but journal doesn't, or vice versa)
  const catalogPath = path.join(edsDir, 'features', 'feature_catalog.json');
  const journalPath = path.join(edsDir, 'features', 'feature_journal.md');
  if (fs.existsSync(catalogPath) && !fs.existsSync(journalPath)) {
    issues.push('Feature catalog exists without a journal — journal should track rounds');
  }

  // Check: experiment log has entries but no champion.json
  const logPath = path.join(edsDir, 'models', 'experiment_log.json');
  const championPath = path.join(edsDir, 'models', 'champion.json');
  if (fs.existsSync(logPath)) {
    try {
      const log = JSON.parse(fs.readFileSync(logPath, 'utf8'));
      const exps = log.experiments || [];
      if (exps.length >= 3 && !fs.existsSync(championPath)) {
        issues.push(`${exps.length} experiments logged but no champion selected yet`);
      }
    } catch (e) {
      // best-effort
    }
  }

  return issues;
}

function main() {
  const edsRoot = findEdsRoot();
  if (!edsRoot) return; // not an EDS project — nothing to wrap up

  const issues = checkConsistency(edsRoot);
  if (issues.length > 0) {
    const lines = ['[eds-wrap] Session-end consistency check:'];
    for (const issue of issues) {
      lines.push(`  - ${issue}`);
    }
    console.error(lines.join('\n'));
  }
}

try {
  main();
} catch (e) {
  // Silent fail — wrap-up must never block Stop.
}
