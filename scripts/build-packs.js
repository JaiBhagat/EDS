#!/usr/bin/env node
// EDS — selective-install builder. Generates a plugin-shaped output
// directory containing only the chosen profile's core skills plus any
// explicitly requested packs, copied flat into <out>/skills/ (Claude
// Code discovers any directory with a SKILL.md under the plugin's
// declared "skills" path — it doesn't care whether the source was
// skills/ or skills-packs/).
//
// Usage:
//   node scripts/build-packs.js --list
//   node scripts/build-packs.js --profile core --out /path/to/output
//   node scripts/build-packs.js --profile full --with production:model-governance,domains:credit-risk --out /path/to/output

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');

// Profiles are core-skill selections only. Packs are always additive via
// --with, regardless of profile (minimal + a pack is a valid combination).
const PROFILES = {
  minimal: ['eds-core', 'discovery'],
  core: ['eds-core', 'discovery', 'data-audit', 'leakage-check', 'evaluation-design', 'label-design', 'decision-optimization', 'baseline-first', 'fde'],
  full: ['eds-core', 'discovery', 'data-audit', 'leakage-check', 'evaluation-design', 'label-design', 'decision-optimization', 'baseline-first', 'fde', 'eda-workflow', 'experiment-design', 'error-analysis', 'model-monitoring', 'ds-reporting', 'notebook-hygiene'],
};
const PACK_CATEGORIES = ['methods', 'production', 'domains'];
const ALWAYS_COPY = ['.claude-plugin', 'EDS.md', 'commands', 'hooks', 'rules'];

function discoverPacks() {
  const packs = {}; // "category:name" -> absolute source path
  for (const category of PACK_CATEGORIES) {
    const dir = path.join(ROOT, 'skills-packs', category);
    if (!fs.existsSync(dir)) continue;
    for (const name of fs.readdirSync(dir)) {
      const full = path.join(dir, name);
      if (fs.statSync(full).isDirectory() && fs.existsSync(path.join(full, 'SKILL.md'))) {
        packs[`${category}:${name}`] = full;
      }
    }
  }
  return packs;
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(s, d);
    } else {
      fs.copyFileSync(s, d);
    }
  }
}

function parseArgs(argv) {
  const args = { with: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--list') args.list = true;
    else if (a === '--profile') args.profile = argv[++i];
    else if (a === '--with') args.with = argv[++i].split(',').map((s) => s.trim()).filter(Boolean);
    else if (a === '--out') args.out = argv[++i];
  }
  return args;
}

function printList(packs) {
  console.log('Profiles (core skills):');
  for (const [name, skills] of Object.entries(PROFILES)) {
    console.log(`  ${name}: ${skills.join(', ')}`);
  }
  console.log('\nAvailable packs (--with):');
  for (const key of Object.keys(packs).sort()) {
    console.log(`  ${key}`);
  }
}

function build(args, packs) {
  if (!args.profile || !PROFILES[args.profile]) {
    console.error(`--profile must be one of: ${Object.keys(PROFILES).join(', ')}`);
    process.exit(1);
  }
  if (!args.out) {
    console.error('--out <dir> is required');
    process.exit(1);
  }
  const unknown = args.with.filter((tag) => !packs[tag]);
  if (unknown.length > 0) {
    console.error(`unknown pack(s): ${unknown.join(', ')} — run --list to see available packs`);
    process.exit(1);
  }

  const outSkillsDir = path.join(args.out, 'skills');
  fs.mkdirSync(outSkillsDir, { recursive: true });

  const coreSkills = PROFILES[args.profile];
  for (const name of coreSkills) {
    const src = path.join(ROOT, 'skills', name);
    if (!fs.existsSync(src)) {
      console.error(`core skill '${name}' not found at ${src} — repo layout may have changed since this profile was defined`);
      process.exit(1);
    }
    copyDir(src, path.join(outSkillsDir, name));
  }

  const packTag = args.profile === 'full' && args.with.length === 0
    ? Object.keys(packs) // 'full' with no explicit --with means every pack
    : args.with;
  for (const tag of packTag) {
    const [, name] = tag.split(':');
    copyDir(packs[tag], path.join(outSkillsDir, name));
  }

  for (const item of ALWAYS_COPY) {
    const src = path.join(ROOT, item);
    if (!fs.existsSync(src)) continue;
    const dest = path.join(args.out, item);
    if (fs.statSync(src).isDirectory()) copyDir(src, dest);
    else fs.copyFileSync(src, dest);
  }

  console.log(`Built '${args.profile}' profile (${coreSkills.length} core skill(s)) + ${packTag.length} pack(s) to ${args.out}`);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const packs = discoverPacks();
  if (args.list || (!args.profile && !args.out)) {
    printList(packs);
    return;
  }
  build(args, packs);
}

main();
