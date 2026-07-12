#!/usr/bin/env node
// EDS — CI drift check for generated adapter copies (Phase 5). Regenerates
// each adapter's expected content from EDS.md + rules/common/*.md in memory
// and diffs it against what's committed. Never writes — run
// scripts/generate-adapters.js to fix drift, this script only reports it.
//
// Usage: node scripts/check-rule-copies.js
// Exit 0: all copies match. Exit 1: at least one is stale or missing.

const fs = require('fs');
const path = require('path');
const { buildRuleText } = require('./lib/rule-text');

const ROOT = path.join(__dirname, '..');

function cursorFrontmatter() {
  return ['---', 'description: EDS ruleset (generated)', 'alwaysApply: true', '---', ''].join(
    '\n'
  );
}

function checkOne(label, targetPath, expected) {
  if (!fs.existsSync(targetPath)) {
    console.error(`MISSING: ${label} (${path.relative(ROOT, targetPath)})`);
    return false;
  }
  const actual = fs.readFileSync(targetPath, 'utf8');
  if (actual !== expected) {
    console.error(`STALE: ${label} (${path.relative(ROOT, targetPath)}) — run scripts/generate-adapters.js`);
    return false;
  }
  return true;
}

function main() {
  const ruleText = buildRuleText(ROOT);
  const checks = [
    checkOne('Cursor rules', path.join(ROOT, '.cursor', 'rules', 'eds.mdc'), cursorFrontmatter() + ruleText),
    checkOne('AGENTS.md', path.join(ROOT, 'AGENTS.md'), ruleText),
    checkOne('Copilot instructions', path.join(ROOT, '.github', 'copilot-instructions.md'), ruleText),
  ];

  if (checks.every(Boolean)) {
    console.log('all adapter copies match EDS.md + rules/common/*.md');
    process.exit(0);
  }
  process.exit(1);
}

main();
