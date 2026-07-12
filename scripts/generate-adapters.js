#!/usr/bin/env node
// EDS — generate adapter copies of the ruleset for harnesses that can't load
// a Claude Code plugin (Cursor, plain AGENTS.md readers, Copilot). Run this
// after editing EDS.md or rules/common/*.md, then commit the regenerated
// files. CI drift check: scripts/check-rule-copies.js.
//
// Usage: node scripts/generate-adapters.js

const fs = require('fs');
const path = require('path');
const { buildRuleText } = require('./lib/rule-text');

const ROOT = path.join(__dirname, '..');

const CURSOR_TARGET = path.join(ROOT, '.cursor', 'rules', 'eds.mdc');
const AGENTS_TARGET = path.join(ROOT, 'AGENTS.md');
const COPILOT_TARGET = path.join(ROOT, '.github', 'copilot-instructions.md');

function cursorFrontmatter() {
  return ['---', 'description: EDS ruleset (generated)', 'alwaysApply: true', '---', ''].join(
    '\n'
  );
}

function writeFile(targetPath, content) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.writeFileSync(targetPath, content);
  console.log(`wrote ${path.relative(ROOT, targetPath)}`);
}

function main() {
  const ruleText = buildRuleText(ROOT);
  writeFile(CURSOR_TARGET, cursorFrontmatter() + ruleText);
  writeFile(AGENTS_TARGET, ruleText);
  writeFile(COPILOT_TARGET, ruleText);
}

main();
