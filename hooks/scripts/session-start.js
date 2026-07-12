#!/usr/bin/env node
// EDS — SessionStart hook.
// Injects: current mode + a condensed EDS.md digest (axioms, ladder, never-cut
// list — never the full skill set) + the Problem Brief if one exists for
// this project. Native Claude Code SessionStart accepts raw stdout as
// context, so no JSON envelope is needed here.

const fs = require('fs');
const path = require('path');

const PLUGIN_ROOT = process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, '..', '..');
const DIGEST_CHAR_BUDGET = 2000;

function getMode() {
  if (process.env.EDS_DEFAULT_MODE) return process.env.EDS_DEFAULT_MODE.trim().toLowerCase();
  try {
    const cfgPath = path.join(require('os').homedir(), '.config', 'eds', 'config.json');
    const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
    if (cfg.mode) return String(cfg.mode).toLowerCase();
  } catch (e) {
    // no config file — fall through to default
  }
  return 'full';
}

// Pull just the operative sections out of EDS.md (axioms, never-cut list —
// the two terse, safety-critical lists) rather than the whole file, and
// never truncate mid-section: a partial never-cut list is worse than none.
// The full ladder + tone rules live in EDS.md and the eds-core skill, which
// trigger on any actual DS work — they don't need to ride on every session start.
function buildDigest(mode) {
  const sections = ['## The six axioms', '## The Never-Cut List'];
  let edsMd = '';
  try {
    edsMd = fs.readFileSync(path.join(PLUGIN_ROOT, 'EDS.md'), 'utf8');
  } catch (e) {
    return `EDS MODE: ${mode.toUpperCase()}. (EDS.md not found at ${PLUGIN_ROOT} — ruleset unavailable this session.)`;
  }

  const lines = edsMd.split(/\r?\n/);
  const headerIdx = (name) => lines.findIndex((l) => l.trim() === name);
  const nextHeaderIdx = (from) => {
    for (let i = from + 1; i < lines.length; i++) {
      if (/^##\s/.test(lines[i])) return i;
    }
    return lines.length;
  };

  let digest = `EDS MODE ACTIVE: ${mode.toUpperCase()}. Switch: /eds lite|full|ultra|off. Full ladder + tone rules: EDS.md.\n\n`;
  for (const name of sections) {
    const start = headerIdx(name);
    if (start === -1) continue;
    const end = nextHeaderIdx(start);
    const sectionText = lines.slice(start, end).join('\n').trim() + '\n\n';
    if (digest.length + sectionText.length > DIGEST_CHAR_BUDGET) break; // drop whole section, never mid-cut
    digest += sectionText;
  }
  return digest.trim();
}

function extractPlanStatus(briefText) {
  const planIdx = briefText.indexOf('## Plan');
  if (planIdx === -1) return null;
  const planText = briefText.slice(planIdx);
  const entries = planText.split(/\r?\n/)
    .filter((l) => /^[-*]\s+/.test(l));
  if (entries.length === 0) return null;

  let done = 0, total = entries.length;
  let nextStage = null, nextGate = null;
  for (const entry of entries) {
    if (/\bdone\b/i.test(entry)) { done++; continue; }
    if (/\bskipped\b/i.test(entry)) { total--; continue; }
    if (!nextStage) {
      // First non-done, non-skipped entry is "next"
      const nameMatch = entry.match(/^[-*]\s+(\S+)/);
      nextStage = nameMatch ? nameMatch[1] : 'unknown';
      nextGate = /user-signoff/i.test(entry) ? 'user-signoff' : 'none';
    }
  }
  let status = `EDS plan: ${done}/${total} done`;
  if (nextStage) {
    status += ` · next: ${nextStage}`;
    if (nextGate === 'user-signoff') status += ` (gate: user signoff)`;
  } else if (done === total) {
    status += ' · all stages complete';
  }
  return status;
}

function findBriefPath() {
  // Look for .eds/BRIEF.md from cwd upward, same convention as .git discovery.
  let dir = process.cwd();
  for (;;) {
    const candidate = path.join(dir, '.eds', 'BRIEF.md');
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function findFeaturesDir() {
  let dir = process.cwd();
  for (;;) {
    const candidate = path.join(dir, '.eds', 'features');
    if (fs.existsSync(path.join(candidate, 'feature_catalog.json'))) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function main() {
  const mode = getMode();
  if (mode === 'off') {
    process.stdout.write('');
    return;
  }

  let output = buildDigest(mode);

  const briefPath = findBriefPath();
  if (briefPath) {
    try {
      const brief = fs.readFileSync(briefPath, 'utf8');
      output += `\n\n---\nExisting Problem Brief found at ${briefPath} — read it before starting new analysis; ` +
        `downstream skills should treat it as ground truth, not re-derive context:\n\n${brief}`;

      // R1.4: emit Plan status line so every session opens knowing where it is
      const planStatus = extractPlanStatus(brief);
      if (planStatus) {
        output += `\n\n${planStatus}`;
      }
    } catch (e) {
      // best-effort — don't block session start over a brief read failure
    }
  } else if (mode !== 'lite') {
    output += '\n\n---\nNo .eds/BRIEF.md found. On a new problem, run /discover before EDA or modeling.';
  }

  const featuresDir = findFeaturesDir();
  if (featuresDir) {
    try {
      const catalog = JSON.parse(fs.readFileSync(path.join(featuresDir, 'feature_catalog.json'), 'utf8'));
      const selected = catalog.filter((e) => e.status === 'selected').length;
      const candidate = catalog.filter((e) => e.status === 'candidate').length;
      output += `\n\n---\nActive FDE campaign: ${catalog.length} cataloged feature(s) (${selected} selected, ${candidate} candidate). ` +
        `See ${path.join(featuresDir, 'selected_features.md')} for the current set — grep feature_journal.md on demand, never bulk-load it.`;
    } catch (e) {
      // best-effort — a malformed catalog shouldn't block session start
    }
  }

  // P3: Lightweight manifest-freshness check (pure JS, no Python subprocess).
  // Full eds-init (with env check + state reconciliation) available via `python scripts/eds_init.py`
  // but NOT called here — pandas/numpy import time (1.5-4s) would frequently timeout the 5s hook.
  if (briefPath) {
    const briefDir = path.dirname(path.dirname(briefPath));
    const manifestPath = path.join(briefDir, '.eds', 'data-manifest.json');
    if (fs.existsSync(manifestPath)) {
      try {
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        const sources = Array.isArray(manifest) ? manifest : (manifest.sources || []);
        const now = Date.now();
        const stale = sources.filter((s) => {
          if (!s || !s.audited_at) return true;
          const age = (now - new Date(s.audited_at).getTime()) / (1000 * 60 * 60 * 24);
          return age > 30;
        });
        if (stale.length > 0) {
          output += `\ndata: ${stale.length} source(s) stale (>30d since audit) — run data-audit to refresh`;
        }
      } catch (e) {
        // best-effort
      }
    }
  }

  process.stdout.write(output);
}

try {
  main();
} catch (e) {
  // Silent fail — SessionStart context is best-effort, must never block a session.
  process.stdout.write('');
}
