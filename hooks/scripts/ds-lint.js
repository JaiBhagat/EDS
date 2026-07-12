#!/usr/bin/env node
// EDS — PostToolUse hook on Edit/Write of .py/.ipynb/.sql.
// Static pitfall lint (regex/AST-lite, deliberately conservative — false
// positives cost more trust than missed catches). Warn-only by default;
// EDS_HOOK_PROFILE=strict additionally blocks (exit 2) on the two worst
// checks (fit-before-split, time-shuffled CV), since those two silently
// invalidate an entire evaluation rather than just being untidy.

const fs = require('fs');
const path = require('path');

const BLOCKING_CHECKS = new Set(['fit-before-split', 'time-shuffle', 'stage-done-without-gate']);
const MODEL_CTORS = /\b(RandomForestClassifier|RandomForestRegressor|GradientBoostingClassifier|GradientBoostingRegressor|LogisticRegression|KMeans|XGBClassifier|XGBRegressor|LGBMClassifier|LGBMRegressor|DecisionTreeClassifier|DecisionTreeRegressor)\s*\(/;
const DATETIME_HINT = /(pd\.to_datetime\(|\.dt\.|datetime64|\bdate_col\b|_date\b|_at\b|_time\b|timestamp)/i;
const METRIC_FNS = /\b(accuracy_score|roc_auc_score|f1_score|precision_score|recall_score|mean_squared_error|mean_absolute_error|r2_score)\s*\(/;
// FDE F5 (a feature is code + data version + rationale, not just a column):
// only fires if this project has an active campaign (.eds/features/feature_catalog.json
// exists) — most sessions don't, so this stays a no-op there. Duplicate-feature
// (construction-hash) detection and target-reference escalation to leakage-hunter
// are deliberately not implemented here yet — those need the candidate's actual
// construction code, not just the assignment line; # eds: deferred — needs a
// richer per-feature code slice than a single-line regex can give reliably.
const NEW_COLUMN_RE = /\bdf(?:\w*)\[['"]([A-Za-z_][A-Za-z0-9_]*)['"]\]\s*=(?!=)|\.assign\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*=/;

function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8');
  } catch (e) {
    return '';
  }
}

function extractSource(filePath) {
  const raw = fs.readFileSync(filePath, 'utf8');
  if (filePath.endsWith('.ipynb')) {
    const nb = JSON.parse(raw);
    const cells = [];
    (nb.cells || []).forEach((cell, i) => {
      if (cell.cell_type === 'code') {
        const src = Array.isArray(cell.source) ? cell.source.join('') : (cell.source || '');
        cells.push({ label: `cell ${i}`, text: src });
      }
    });
    return cells;
  }
  return [{ label: null, text: raw }];
}

function lineRef(label, lineNo) {
  return label ? `${label}, line ${lineNo}` : `line ${lineNo}`;
}

// check 1: fit-before-split — a variable is fit-on before it's passed into train_test_split.
function checkFitBeforeSplit(lines) {
  const findings = [];
  const fitCalls = []; // {var, line}
  const splitCalls = []; // {var, line}
  lines.forEach((line, idx) => {
    let m = line.match(/\.(?:fit|fit_transform)\(\s*([A-Za-z_][A-Za-z0-9_]*)/);
    if (m) fitCalls.push({ var: m[1], line: idx + 1 });
    // also catch the assignment target: `X_scaled = scaler.fit_transform(X)` —
    // it's X_scaled that later leaks into the split, not X.
    m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=.*\.fit_transform\(/);
    if (m) fitCalls.push({ var: m[1], line: idx + 1 });
    m = line.match(/train_test_split\(\s*([A-Za-z_][A-Za-z0-9_]*)/);
    if (m) splitCalls.push({ var: m[1], line: idx + 1 });
  });
  for (const fit of fitCalls) {
    for (const split of splitCalls) {
      if (fit.var === split.var && fit.line < split.line) {
        findings.push({ line: fit.line, message: `.fit(${fit.var}) at this line runs before train_test_split(${split.var}, ...) at line ${split.line} — likely fitting on data that includes the eventual test set` });
      }
    }
  }
  return findings;
}

// check 2: shuffled CV/split on time-indexed data.
function checkTimeShuffle(lines, fullText) {
  if (!DATETIME_HINT.test(fullText)) return [];
  const findings = [];
  lines.forEach((line, idx) => {
    if (/train_test_split\(/.test(line) && !/shuffle\s*=\s*False/.test(line)) {
      findings.push({ line: idx + 1, message: 'train_test_split here defaults to shuffle=True (or sets it explicitly) in a file with time/date signals — a random split on time-indexed data leaks future into past' });
    }
  });
  return findings;
}

// check 3: stochastic calls missing a seed.
function checkSeedMissing(lines) {
  const findings = [];
  lines.forEach((line, idx) => {
    const isStochastic = /train_test_split\(/.test(line) || MODEL_CTORS.test(line);
    if (isStochastic && !/(random_state|seed)\s*=/.test(line)) {
      findings.push({ line: idx + 1, message: 'stochastic call has no random_state/seed — result won\'t reproduce run to run' });
    }
  });
  return findings;
}

// check 4: SELECT * in SQL.
function checkSelectStar(lines, isSql) {
  if (!isSql) return [];
  const findings = [];
  lines.forEach((line, idx) => {
    if (/select\s+\*/i.test(line)) {
      findings.push({ line: idx + 1, message: 'SELECT * has no grain/contract — a schema change silently reshapes every downstream consumer' });
    }
  });
  return findings;
}

// check 5: merge/join with no nearby row-count assertion.
function checkJoinNoAssert(lines) {
  const findings = [];
  lines.forEach((line, idx) => {
    if (/\.merge\(|pd\.merge\(|\bJOIN\b/i.test(line)) {
      const window = lines.slice(idx, idx + 6).join('\n');
      if (!/(assert|\.shape|len\(|COUNT\()/i.test(window)) {
        findings.push({ line: idx + 1, message: 'join here has no row-count assertion/shape check in the next few lines — a fan-out join changes grain silently' });
      }
    }
  });
  return findings;
}

// check 6: dropna with no logging of what was dropped.
function checkDropnaNoLog(lines) {
  const findings = [];
  lines.forEach((line, idx) => {
    if (/\.dropna\(/.test(line)) {
      const window = lines.slice(Math.max(0, idx - 2), idx + 3).join('\n');
      if (!/(len\(|\.shape|print\(|log)/i.test(window)) {
        findings.push({ line: idx + 1, message: 'dropna() here doesn\'t log rows dropped — silent data loss, no way to tell how much was cut' });
      }
    }
  });
  return findings;
}

// check 7: metric computed on the training frame.
function checkEvalOnTrain(lines) {
  const findings = [];
  lines.forEach((line, idx) => {
    const metricCall = METRIC_FNS.test(line) || /\.score\(/.test(line);
    if (metricCall && /train/i.test(line)) {
      findings.push({ line: idx + 1, message: 'metric computed against a variable named/derived from the training frame — this measures fit, not generalization' });
    }
  });
  return findings;
}

// FDE catalog check — separate from CHECKS below since it needs project
// state (the catalog file), not just the edited text.
function findFeatureCatalogPath(fromDir) {
  let dir = fromDir;
  for (;;) {
    const candidate = path.join(dir, '.eds', 'features', 'feature_catalog.json');
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function checkUncatalogedFeature(lines, knownNames) {
  const findings = [];
  lines.forEach((line, idx) => {
    const m = line.match(NEW_COLUMN_RE);
    if (!m) return;
    const colName = m[1] || m[2];
    if (colName && !knownNames.has(colName)) {
      findings.push({ line: idx + 1, message: `new column '${colName}' isn't in feature_catalog.json — uncataloged feature, what's the hypothesis? (register via skills/fde/scripts/catalog.py)` });
    }
  });
  return findings;
}

const CHECKS = [
  { id: 'fit-before-split', run: (lines, text, isSql) => checkFitBeforeSplit(lines), mapsTo: 'never-cut 2 (leakage prevention)' },
  { id: 'time-shuffle', run: (lines, text) => checkTimeShuffle(lines, text), mapsTo: 'never-cut 2 / axiom 4 (time flows one way)' },
  { id: 'seed-missing', run: (lines) => checkSeedMissing(lines), mapsTo: 'never-cut 5 (reproducibility)' },
  { id: 'select-star', run: (lines, text, isSql) => checkSelectStar(lines, isSql), mapsTo: 'never-cut 1 (data validation / grain)' },
  { id: 'join-no-assert', run: (lines) => checkJoinNoAssert(lines), mapsTo: 'never-cut 1 (join cardinality)' },
  { id: 'dropna-no-log', run: (lines) => checkDropnaNoLog(lines), mapsTo: 'never-cut 1 (silent data loss)' },
  { id: 'eval-on-train', run: (lines) => checkEvalOnTrain(lines), mapsTo: 'never-cut 3 (honest evaluation)' },
];

function lintCell(label, text, isSql) {
  const lines = text.split(/\r?\n/);
  const out = [];
  for (const check of CHECKS) {
    for (const f of check.run(lines, text, isSql)) {
      out.push({ id: check.id, mapsTo: check.mapsTo, ref: lineRef(label, f.line), message: f.message });
    }
  }
  return out;
}

// H3 — stage marked done without a passing gate record.
// Fires when BRIEF.md Plan section has a "done" entry without a gate-record reference.
function checkStageWithoutGate(filePath) {
  const findings = [];
  try {
    const text = fs.readFileSync(filePath, 'utf8');
    const planIdx = text.indexOf('## Plan');
    if (planIdx === -1) return findings;
    const planText = text.slice(planIdx);
    const lines = planText.split(/\r?\n/);
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      // Match plan entries like: "- audit · data-audit · done · ..."
      if (/\bdone\b/i.test(line) && /^[-*]\s+/.test(line)) {
        // A done entry must have a gate-record ref (path or "gate: <ref>")
        if (!/gate[-_]record|verification\/|\.json\b/i.test(line)) {
          findings.push({
            id: 'stage-done-without-gate',
            mapsTo: 'H3 (no green gate, no done)',
            ref: `Plan line ${i + 1}`,
            message: `stage marked "done" without a gate-record reference — run the stage gate first`,
          });
        }
      }
    }
  } catch (e) {
    // best-effort
  }
  return findings;
}

// H4 — scope-guard: warn when writes fall outside current stage's expected surface.
// Patterns match against the FILENAME component (not the full path) to avoid false
// positives on innocent paths like "data_model.py" or "training_data.csv".
const STAGE_SURFACE_MAP = {
  'discovery': [/BRIEF\.md/, /\.eds\//, /probes?\//],
  'data-audit': [/\.eds\/data-manifest/, /\baudit/i, /\.eds\/verification\//],
  'eda': [/\beda[_./]/i, /\bexplor/i, /\.ipynb$/, /\bplots?\//i, /\bfigures?\//i],
  'fde': [/\bfeature[_s]/i, /\.eds\/features\//, /\bfunnel/i, /\bcatalog/i],
  'baseline': [/\bbaseline/i, /\.eds\/models\//, /\bbaselines\.py/],
  'model': [/\.eds\/models\//, /\btrain_\w+\.py/i, /\bexperiment/i, /\bmodel_/i],
  'decision-optimization': [/\bthreshold/i, /\bdecision_opt/i, /\bcutoff/i, /operating.?point/i],
  'report': [/\breport/i, /\bdeliverable/i, /\bsummary/i, /\bfindings/i],
};

function getCurrentStage(projectRoot) {
  try {
    // Fast path: read the one-line cache (written by scripts/state/plan.py on transitions)
    const cachePath = path.join(projectRoot, '.eds', '.current-stage');
    if (fs.existsSync(cachePath)) {
      const cached = fs.readFileSync(cachePath, 'utf8').trim();
      if (cached) return cached;
    }
    // Fallback: parse BRIEF.md (only if cache missing — first session or old project)
    const briefPath = path.join(projectRoot, '.eds', 'BRIEF.md');
    if (!fs.existsSync(briefPath)) return null;
    const text = fs.readFileSync(briefPath, 'utf8');
    const planIdx = text.indexOf('## Plan');
    if (planIdx === -1) return null;
    const planText = text.slice(planIdx);
    const match = planText.match(/^[-*]\s+(\S+).*\bin-progress\b/im);
    return match ? match[1].replace(/[·\s]/g, '') : null;
  } catch (e) {
    return null;
  }
}

// Shared: walk up from a file to find the .eds/ project root (used by scope-guard and catalog check)
function findProjectRoot(fromPath) {
  let dir = path.dirname(fromPath);
  for (let i = 0; i < 10; i++) {
    if (fs.existsSync(path.join(dir, '.eds'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
  return null;
}

function checkScopeGuard(filePath, projectRoot) {
  const findings = [];
  if (!projectRoot) return findings;

  const currentStage = getCurrentStage(projectRoot);
  if (!currentStage) return findings;

  const patterns = STAGE_SURFACE_MAP[currentStage];
  if (!patterns) return findings;

  const relPath = path.relative(projectRoot, filePath);
  const matchesSurface = patterns.some((re) => re.test(relPath));
  if (!matchesSurface) {
    findings.push({
      id: 'scope-guard',
      mapsTo: 'H4 (one stage at a time)',
      ref: relPath,
      message: `write to "${relPath}" while current stage is "${currentStage}" — file doesn't match expected surface for this stage`,
    });
  }
  return findings;
}

function main() {
  const raw = readStdin();
  let input;
  try {
    input = JSON.parse(raw);
  } catch (e) {
    return;
  }
  const filePath = input.tool_input && input.tool_input.file_path;
  if (!filePath || !fs.existsSync(filePath)) return;

  // H3/H4 checks fire on .eds/BRIEF.md writes; code lint fires on .py/.ipynb/.sql
  const isBrief = filePath.includes('.eds') && path.basename(filePath) === 'BRIEF.md';
  const isCodeFile = /\.(py|ipynb|sql)$/.test(filePath);
  if (!isBrief && !isCodeFile) return;

  const profile = process.env.EDS_HOOK_PROFILE || 'standard';
  const disabled = (process.env.EDS_DISABLED_HOOKS || '').split(',').map((s) => s.trim());
  if (profile === 'minimal' || disabled.includes('ds-lint')) return;

  // Single upward walk for the project root — shared by scope-guard and catalog check
  const projectRoot = isCodeFile ? findProjectRoot(filePath) : null;

  let findings = [];

  // H3: stage-done-without-gate (fires on BRIEF.md edits)
  if (isBrief) {
    findings = findings.concat(checkStageWithoutGate(filePath));
  }

  // H4: scope-guard (fires on all code writes when a Plan is active)
  if (isCodeFile) {
    findings = findings.concat(checkScopeGuard(filePath, projectRoot));
  }

  // Code lint checks (only for .py/.ipynb/.sql)
  if (isCodeFile) {
    const isSql = filePath.endsWith('.sql');
    const cells = extractSource(filePath);
    for (const cell of cells) {
      findings = findings.concat(lintCell(cell.label, cell.text, isSql));
    }

    // Use projectRoot for catalog lookup instead of a second directory walk
    const catalogPath = !isSql && projectRoot && fs.existsSync(path.join(projectRoot, '.eds', 'features', 'feature_catalog.json'))
      ? path.join(projectRoot, '.eds', 'features', 'feature_catalog.json')
      : (!isSql ? findFeatureCatalogPath(path.dirname(filePath)) : null);
    if (catalogPath) {
      try {
        const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
        const knownNames = new Set(catalog.map((e) => e.name));
        for (const cell of cells) {
          const lines = cell.text.split(/\r?\n/);
          for (const f of checkUncatalogedFeature(lines, knownNames)) {
            findings.push({ id: 'uncataloged-feature', mapsTo: 'FDE F5 (feature = code + data version + rationale)', ref: lineRef(cell.label, f.line), message: f.message });
          }
        }
      } catch (e) {
        // best-effort — a malformed catalog shouldn't block linting the rest
      }
    }
  }

  if (findings.length === 0) return;

  const blocking = profile === 'strict' && findings.filter((f) => BLOCKING_CHECKS.has(f.id));
  const lines = [`[ds-lint] ${findings.length} finding(s) in ${filePath}:`];
  for (const f of findings) {
    lines.push(`  - ${f.ref}: ${f.message} [${f.mapsTo}]`);
  }
  console.error(lines.join('\n'));

  if (blocking && blocking.length > 0) {
    process.exit(2);
  }
}

try {
  main();
} catch (e) {
  // Silent fail — lint is best-effort, must never block a tool call it can't parse.
}
