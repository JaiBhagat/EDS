// EDS — shared rule-text assembly. EDS.md is the single canonical source;
// every adapter copy (Cursor, AGENTS.md, Copilot) is generated from the same
// concatenation so there is exactly one place to edit the ruleset.
'use strict';

const fs = require('fs');
const path = require('path');

const SOURCES = [
  'EDS.md',
  'rules/common/rigor.md',
  'rules/common/reproducibility.md',
  'rules/common/communication.md',
];

const BANNER =
  '<!-- GENERATED FILE — do not edit directly. Source: EDS.md + rules/common/*.md. ' +
  'Regenerate with `node scripts/generate-adapters.js` after editing a source file. -->';

function buildRuleText(rootDir) {
  const parts = SOURCES.map((rel) =>
    fs.readFileSync(path.join(rootDir, rel), 'utf8').trimEnd()
  );
  return [BANNER, '', parts.join('\n\n---\n\n'), ''].join('\n');
}

module.exports = { SOURCES, BANNER, buildRuleText };
