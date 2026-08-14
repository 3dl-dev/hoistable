export const meta = {
  name: 'ouroboros',
  description: 'The loss function. Emit each app as a SELF-CONTAINED hoist skill, then a fresh agent, given ONLY that skill file (no repo, nothing of ours to fetch), follows it in its own session to hoist and honestly grade the app on a real target with ordinary tools. It grades the product a stranger actually receives, an agent following a skill, never our code running. The honest transfer over that whole run is the loss, up-altitude, outranking any code-mechanics check.',
  phases: [
    { title: 'Emit', detail: 'assemble each app self-contained skill into a clean dir' },
    { title: 'Grade', detail: 'a fresh agent follows each skill and hoists the app, no repo access' }
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
    followed_skill_only: { type: 'boolean' },
    note: { type: 'string' }
  },
  required: ['app', 'outcome', 'transfer_passed', 'transfer_total', 'followed_skill_only']
}

function receiverPrompt(app, skillPath) {
  return [
    'You are a RECEIVER on a clean machine. Someone shared ONE file with you:',
    '  ' + skillPath,
    'It is a self-contained hoist skill for "' + app + '". Install and follow it exactly to',
    'bring the app up and grade it, in THIS session, with ordinary tools (git, the container',
    'runtime, a shell).',
    '',
    'HARD RULES (fair-transfer test):',
    '- Use ONLY what the skill file itself carries, plus standard tools already on the box.',
    "  The skill is self-contained: there is nothing of ours to fetch, no toolchain, no",
    '  runtime, no CLI. Do NOT read, cd into, or use the hoistable source repo at ' + REPO,
    '  or any other hoistable checkout. (The skill\'s own recipe may tell you to clone the',
    "  APP's source; that is fine, it is part of the recipe.)",
    '- You do the work yourself, in context, following the honest-grade discipline the skill',
    '  spells out: binds gate, resolve isolation, preflight (deploy nothing), deploy in an',
    '  isolated namespace or sandbox, health, held-back acceptance, always tear down and',
    '  verify no residue.',
    '- Deploy only into isolated namespaces, tear them down, leave the host clean.',
    '- If a required bind or isolation strength is missing, report cannot-build and name it.',
    '  Never fake success; a truthful cannot-build is a valid result.',
    '',
    'Return the verdict: outcome (built / honest-failure / cannot-build), how many acceptance',
    'checks passed of the total, whether you followed the skill alone (no repo of ours, nothing',
    'fetched), and a short note.'
  ].join('\n')
}

phase('Emit')
const setup = await agent(
  [
    'In ' + REPO + ": assemble each app's SELF-CONTAINED hoist skill so a receiver grades the",
    'product a stranger actually gets: an agent following a skill, not our code.',
    'Apps: ' + JSON.stringify(APPS) + '.',
    'Steps:',
    '1. Pick a fresh work dir under /tmp (call it <work>).',
    '2. For each app, assemble its skill with core/builder/emit.py emit_skill(config), writing',
    '   it to <work>/<app>/<app>.SKILL.md. The emitted skill is self-contained: it carries the',
    '   recipe and the honest-grade discipline as prose, and pins NO toolchain (there is none).',
    '   Configs:',
    '   - agent-dyno: ~/projects/agent-dyno/hoist/config.json, but OVERRIDE source.clone to the',
    '     public https://github.com/3dl-dev/agent-dyno.git',
    '   - honcho: ' + REPO + '/examples/honcho/config.json',
    '   - hoistable: ' + REPO + '/examples/hoistable/config.json',
    'Return work_dir and each app skill_path. Receivers follow the skill in their own session;',
    'nothing of ours is fetched or run, so this grades the shipped product end to end.'
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
log('OUROBOROS LOSS: ' + line + '  ::  ' + (pass ? 'PASS (product graded via the skill)' : 'FAIL (product not fully graded)'))
return { pass, line, verdicts: scored }
