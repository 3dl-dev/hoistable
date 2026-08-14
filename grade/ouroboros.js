export const meta = {
  name: 'ouroboros',
  description: 'The loss function. Emit each app skill pinned to the PUBLISHED operators release, then a fresh receiver agent, given ONLY the skill (no repo), fetches that published kit, self-extracts it, and hoists the app on a real target. It grades the shipped artifact end to end, never local code. The honest transfer over that whole tower is the loss, up-altitude, outranking the .py mechanics suite.',
  phases: [
    { title: 'Emit', detail: 'build a kit and emit each app skill into a clean dir' },
    { title: 'Grade', detail: 'a fresh receiver agent grades each skill with no repo access' }
  ]
}

const REPO = '/home/baron/projects/hoistable'
const APPS = (args && args.apps) || ['agent-dyno', 'honcho', 'hoistable']

const SETUP_SCHEMA = {
  type: 'object',
  properties: {
    work_dir: { type: 'string' },
    emitted: {
      type: 'array',
      items: {
        type: 'object',
        properties: { app: { type: 'string' }, skill_path: { type: 'string' } },
        required: ['app', 'skill_path']
      }
    }
  },
  required: ['emitted']
}

const VERDICT = {
  type: 'object',
  properties: {
    app: { type: 'string' },
    outcome: { type: 'string', enum: ['built', 'honest-failure', 'cannot-build'] },
    transfer_passed: { type: 'integer' },
    transfer_total: { type: 'integer' },
    self_extracted: { type: 'boolean' },
    note: { type: 'string' }
  },
  required: ['app', 'outcome', 'transfer_passed', 'transfer_total', 'self_extracted']
}

function receiverPrompt(app, skillPath) {
  return [
    'You are a RECEIVER on a clean machine. Someone shared one skill file with you:',
    '  ' + skillPath,
    'Install and follow it exactly to bring up "' + app + '" and grade it.',
    '',
    'HARD RULES (fair-transfer test):',
    '- Use ONLY what the skill file carries, plus standard tools. Do NOT read, cd into, or',
    '  use the hoistable source repo at ' + REPO + ' or any other hoistable checkout. The',
    '  harness must come from the skill\'s own pin: fetch the tarball, verify its sha256 by',
    '  hand, unpack it, and let the extracted kit drive.',
    '- Work under a fresh dir you create. Deploy only into isolated namespaces, tear them',
    '  down, and leave the host clean.',
    '- If a required bind or substrate is missing, or a checksum fails, report cannot-build',
    '  and name it. Never fake success; a truthful cannot-build is a valid result.',
    '',
    'Return the verdict: outcome (built / honest-failure / cannot-build), how many acceptance',
    'checks passed of the total, whether you self-extracted the harness from the pin (not the',
    'repo), and a short note.'
  ].join('\n')
}

phase('Emit')
const setup = await agent(
  [
    'In ' + REPO + ": emit each app's skill so a receiver grades the PUBLISHED ARTIFACT, not local code.",
    'Apps: ' + JSON.stringify(APPS) + '.',
    'Steps:',
    '1. Read the PUBLISHED operators pin from the committed plugin: the fenced json block in',
    '   plugins/hoistable/skills/build/SKILL.md carries version, url, sha256. That url is the',
    '   release a stranger actually fetches. Use that pin as-is; do NOT build a local kit.',
    '2. Pick a fresh work dir under /tmp (call it <work>).',
    '3. For each app, emit its skill with core/builder/emit.py emit_skill(config, pin) using that',
    '   PUBLISHED pin, writing it to <work>/<app>/<app>.SKILL.md. Configs:',
    '   - agent-dyno: ~/projects/agent-dyno/hoist/config.json, but OVERRIDE source.clone to the',
    '     public https://github.com/3dl-dev/agent-dyno.git',
    '   - honcho: ' + REPO + '/examples/honcho/config.json',
    '   - hoistable: ' + REPO + '/examples/hoistable/config.json',
    'Return work_dir and each app skill_path. Receivers fetch the published kit from the pin url,',
    'so this grades the shipped artifact end to end, never local code.'
  ].join('\n'),
  { schema: SETUP_SCHEMA, phase: 'Emit', label: 'emit-skills' }
)

phase('Grade')
const verdicts = await parallel(
  (setup.emitted || []).map(e => () =>
    agent(receiverPrompt(e.app, e.skill_path), { schema: VERDICT, phase: 'Grade', label: 'grade:' + e.app })
  )
)

const scored = verdicts.filter(Boolean)
const line = scored.map(v => v.app + ' ' + v.outcome + ' ' + v.transfer_passed + '/' + v.transfer_total).join('  |  ')
const pass = scored.length === (setup.emitted || []).length && scored.every(v => v.outcome === 'built')
log('OUROBOROS LOSS: ' + line + '  ::  ' + (pass ? 'PASS (release-gradeable)' : 'FAIL (product not fully graded)'))
return { pass, line, verdicts: scored }
