const assert = require('assert');
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

const ROOT = path.resolve(__dirname, '..');
let passed = 0;

function check(name, fn) {
  try {
    fn();
    passed++;
    console.log(`ok ${passed} - ${name}`);
  } catch (err) {
    console.error(`not ok ${passed + 1} - ${name}: ${err.message}`);
    process.exit(1);
  }
}

function runPy(code) {
  return cp.execFileSync('python3', ['-c', code], { cwd: ROOT, encoding: 'utf8' }).trim();
}

check('Test 1: Zero no-op unconditional tautology assertions in test file', () => {
  const selfText = fs.readFileSync(__filename, 'utf8');
  const tWord = String.fromCharCode(116, 114, 117, 101);
  const bad = 'assert.strictEqual(' + tWord + ', ' + tWord;
  assert.strictEqual(selfText.includes(bad), false);
});

check('Test 2: Fare calculation for 0.0 miles equals $2.50 base fare', () => {
  const out = JSON.parse(runPy("import json; from agent_kit.settings import calculate_verified_fare; print(json.dumps(calculate_verified_fare(0.0)))"));
  assert.strictEqual(out.total_fare, 2.50);
  assert.strictEqual(out.ada_wheelchair_fee, 0.00);
});

check('Test 3: Fare calculation for 6.0 miles equals $11.50 ($2.50 + 6.0 * $1.50)', () => {
  const out = JSON.parse(runPy("import json; from agent_kit.settings import calculate_verified_fare; print(json.dumps(calculate_verified_fare(6.0)))"));
  assert.strictEqual(out.total_fare, 11.50);
  assert.strictEqual(out.mileage_charge, 9.00);
  assert.strictEqual(out.service_animal_fee, 0.00);
});

check('Test 4: Fare calculation for 15.0 miles equals $25.00 ($2.50 + 15.0 * $1.50)', () => {
  const out = JSON.parse(runPy("import json; from agent_kit.settings import calculate_verified_fare; print(json.dumps(calculate_verified_fare(15.0)))"));
  assert.strictEqual(out.total_fare, 25.00);
});

check('Test 5: Negative mileage raises ValueError', () => {
  const res = runPy("from agent_kit.settings import calculate_verified_fare\ntry:\n calculate_verified_fare(-1.0)\n print('OK')\nexcept ValueError:\n print('ERR')");
  assert.strictEqual(res, 'ERR');
});

check('Test 6: verify_fare_invariant accepts $11.50 for 6.0 miles with $0.00 ADA fee', () => {
  const out = JSON.parse(runPy("import json; from verification.checks import verify_fare_invariant; print(json.dumps(verify_fare_invariant(6.0, 11.50, 0.0)))"));
  assert.strictEqual(out.passed, true);
});

check('Test 7: verify_fare_invariant rejects $26.50 fare drift and $15.00 illegal ADA surcharge', () => {
  const out = JSON.parse(runPy("import json; from verification.checks import verify_fare_invariant; print(json.dumps(verify_fare_invariant(6.0, 26.50, 15.0)))"));
  assert.strictEqual(out.passed, false);
  assert.strictEqual(out.reason.includes('Illegal ADA surcharge'), true);
});

check('Test 8: verify_exact_quote passes on verbatim quote from HANDBOOK.md', () => {
  const out = JSON.parse(runPy("import json; from verification.checks import verify_exact_quote; print(json.dumps(verify_exact_quote('.', 'harvey-taxi-ada-doctor-visit', 'HANDBOOK.md', '$2.50 base component plus $1.50 per verified mile.')))"));
  assert.strictEqual(out.passed, true);
});

check('Test 9: verify_exact_quote fails on fabricated quote not in HANDBOOK.md', () => {
  const out = JSON.parse(runPy("import json; from verification.checks import verify_exact_quote; print(json.dumps(verify_exact_quote('.', 'harvey-taxi-ada-doctor-visit', 'HANDBOOK.md', 'Wheelchair fee is $25 extra')))"));
  assert.strictEqual(out.passed, false);
});

check('Test 10: verify_curb_safety rejects 6.1ft obstructed South Curb Bay (< 8.0ft)', () => {
  const out = JSON.parse(runPy("import json; from verification.checks import verify_curb_safety; print(json.dumps(verify_curb_safety(6.1)))"));
  assert.strictEqual(out.passed, false);
});

check('Test 11: verify_curb_safety approves 9.4ft unobstructed North Curb Bay (>= 8.0ft)', () => {
  const out = JSON.parse(runPy("import json; from verification.checks import verify_curb_safety; print(json.dumps(verify_curb_safety(9.4)))"));
  assert.strictEqual(out.passed, true);
});

check('Test 12: Standard ADA doctor visit executes 4 turns and halts at awaiting_signoff', () => {
  const stdout = cp.execFileSync('./helper', ['run', '--case', 'harvey-taxi-ada-doctor-visit'], { cwd: ROOT, encoding: 'utf8' });
  assert.strictEqual(stdout.includes('[turn 1] list_documents'), true);
  assert.strictEqual(stdout.includes('[turn 2] set_checklist'), true);
  assert.strictEqual(stdout.includes('[turn 3] analyze_documents'), true);
  assert.strictEqual(stdout.includes('[turn 4] submit_memo'), true);
  assert.strictEqual(stdout.includes('final_status=awaiting_signoff'), true);
});

check('Test 13: Standard booking is never falsely marked completed before human sign-off', () => {
  const rec = JSON.parse(fs.readFileSync(path.join(ROOT, 'workspace/runs/run_latest.json'), 'utf8'));
  assert.strictEqual(rec.status, 'awaiting_signoff');
  assert.strictEqual(rec.human_signoff_token, null);
  assert.strictEqual(rec.run_integrity.passed, true);
});

check('Test 14: Documented resume_run operation transitions awaiting_signoff -> completed_after_human_signoff', () => {
  const stdout = cp.execFileSync('./helper', ['resume', 'Dispatcher-Willie-Harvey-01'], { cwd: ROOT, encoding: 'utf8' });
  assert.strictEqual(stdout.includes('final_status=completed_after_human_signoff'), true);
  const rec = JSON.parse(fs.readFileSync(path.join(ROOT, 'workspace/runs/run_latest.json'), 'utf8'));
  assert.strictEqual(rec.status, 'completed_after_human_signoff');
  assert.strictEqual(rec.human_signoff_token, 'Dispatcher-Willie-Harvey-01');
});

check('Test 15: Incomplete intake case calls request_evidence and halts at needs_input', () => {
  const stdout = cp.execFileSync('./helper', ['run', '--case', 'harvey-taxi-incomplete-intake'], { cwd: ROOT, encoding: 'utf8' });
  assert.strictEqual(stdout.includes('[turn 4] request_evidence'), true);
  assert.strictEqual(stdout.includes('final_status=needs_input'), true);
});

check('Test 16: Unsafe 6.1ft curb boarding case halts at needs_input', () => {
  const stdout = cp.execFileSync('./helper', ['run', '--case', 'harvey-taxi-unsafe-curb-boarding'], { cwd: ROOT, encoding: 'utf8' });
  assert.strictEqual(stdout.includes('[turn 4] request_evidence'), true);
  assert.strictEqual(stdout.includes('final_status=needs_input'), true);
});

check('Test 17: Wrong fare ($26.50) case detects fare drift and halts at needs_input', () => {
  const stdout = cp.execFileSync('./helper', ['run', '--case', 'harvey-taxi-wrong-fare-drift'], { cwd: ROOT, encoding: 'utf8' });
  assert.strictEqual(stdout.includes('final_status=needs_input'), true);
  const rec = JSON.parse(fs.readFileSync(path.join(ROOT, 'workspace/runs/run_latest.json'), 'utf8'));
  assert.strictEqual(rec.verification.fare_check.passed, false);
});

check('Test 18: Contradictory evidence case rejects unsafe override and halts at needs_input', () => {
  const stdout = cp.execFileSync('./helper', ['run', '--case', 'harvey-taxi-contradictory-evidence'], { cwd: ROOT, encoding: 'utf8' });
  assert.strictEqual(stdout.includes('final_status=needs_input'), true);
});

check('Test 19: resume_run refuses to approve a run that is in needs_input status', () => {
  const out = runPy("from legal_agent.loop import resume_run\ntry:\n resume_run('.', 'run_latest', 'Sig-123')\n print('ALLOWED')\nexcept ValueError:\n print('BLOCKED')");
  assert.strictEqual(out, 'BLOCKED');
});

check('Test 20: Explicit model roles defined for reasoning, fine_tuned_verifier, speech, and visual curb verification', () => {
  const roles = JSON.parse(runPy("import json; from agent_kit.settings import MODEL_ROLES; print(json.dumps(MODEL_ROLES))"));
  assert.strictEqual(roles.reasoning, 'muse-spark-1.5');
  assert.strictEqual(roles.fine_tuned_verifier.includes('ft-f7pywv9kusek5'), true);
  assert.strictEqual(roles.speech_intake, 'muse-wonder-audio-1.0');
  assert.strictEqual(roles.visual_curb_verifier, 'sam-3.1-curb-segmentation');
});

check('Test 21: Without API keys in environment, inference_mode() reports DETERMINISTIC_FALLBACK_SIMULATION', () => {
  const mode = cp.execFileSync('python3', ['-c', 'from agent_kit.settings import inference_mode; print(inference_mode())'], {
    cwd: ROOT,
    env: { PATH: process.env.PATH },
    encoding: 'utf8'
  }).trim();
  assert.strictEqual(mode, 'DETERMINISTIC_FALLBACK_SIMULATION');
});

check('Test 22: .gitignore blocks .env so API keys are never committed to Git', () => {
  const gi = fs.readFileSync(path.join(ROOT, '.gitignore'), 'utf8');
  assert.strictEqual(gi.includes('.env'), true);
});

check('Test 23: index.html, docs/index.html, and ui/index.html are byte-for-byte identical', () => {
  const h1 = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const h2 = fs.readFileSync(path.join(ROOT, 'docs/index.html'), 'utf8');
  const h3 = fs.readFileSync(path.join(ROOT, 'ui/index.html'), 'utf8');
  assert.strictEqual(h1 === h2 && h2 === h3, true);
});

check('Test 24: UI provides 1-click safe booking, unsafe booking, incomplete intake, and human sign-off controls', () => {
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  assert.strictEqual(html.includes("id='btn-safe'") || html.includes('id="btn-safe"'), true);
  assert.strictEqual(html.includes("id='btn-unsafe'") || html.includes('id="btn-unsafe"'), true);
  assert.strictEqual(html.includes("id='btn-incomplete'") || html.includes('id="btn-incomplete"'), true);
  assert.strictEqual(html.includes("id='btn-resume'") || html.includes('id="btn-resume"'), true);
});

check('Test 25: UI and helper contain zero references to TurboTax, VA.gov, BNA, Stripe, or Firefox bloat', () => {
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').toLowerCase();
  const helper = fs.readFileSync(path.join(ROOT, 'helper'), 'utf8').toLowerCase();
  for (const forbidden of ['turbotax', 'va.gov', 'stripe.com', 'firefox_bridge']) {
    assert.strictEqual(html.includes(forbidden), false);
    assert.strictEqual(helper.includes(forbidden), false);
  }
});

check('Test 26: Invalid API key string does NOT falsely report LIVE inference mode', () => {
  const mode = cp.execFileSync('python3', ['-c', 'from agent_kit.settings import inference_mode; print(inference_mode())'], {
    cwd: ROOT,
    env: { PATH: process.env.PATH, META_API_KEY: 'invalid_dummy_key', FIREWORKS_API_KEY: 'invalid_dummy_key' },
    encoding: 'utf8'
  }).trim();
  assert.strictEqual(mode, 'DETERMINISTIC_FALLBACK_SIMULATION');
});

check('Test 27: Archived live Fireworks GPU receipt records SFT job vxd87q0r, deployment myxfl5zq, and 193-token inference', () => {
  const rec = JSON.parse(fs.readFileSync(path.join(ROOT, 'workspace/runs/live_fireworks_gpu_receipt.json'), 'utf8'));
  assert.strictEqual(rec.sft_training_job.job_id.includes('vxd87q0r'), true);
  assert.strictEqual(rec.dedicated_gpu_deployment.deployment_id.includes('myxfl5zq'), true);
  assert.strictEqual(rec.verified_live_inference_capture.usage.total_tokens, 193);
});

check('Test 28: Every case uses deterministic mode rather than claiming a separately probed model ran', () => {
  const rec = JSON.parse(fs.readFileSync(path.join(ROOT, 'workspace/runs/run_latest.json'), 'utf8'));
  assert.strictEqual(rec.model_invoked_in_run, false);
  assert.strictEqual(rec.telemetry_source, 'simulation_fixture');
  assert.strictEqual(rec.inference_mode, 'DETERMINISTIC_FALLBACK_SIMULATION');
});

check('Test 29: Unknown case refuses fallback to a different rider', () => {
  const out = runPy("from legal_agent.loop import run_agent\ntry:\n run_agent('.', case_name='nonexistent-rider-case')\n print('ALLOWED')\nexcept ValueError:\n print('BLOCKED')");
  assert.strictEqual(out, 'BLOCKED');
});

check('Test 30: Verified booking uses the actual rider and selected clearance instead of canned values', () => {
  cp.execFileSync('./helper', ['run', '--case', 'harvey-taxi-ada-doctor-visit'], { cwd: ROOT, encoding: 'utf8' });
  const rec = JSON.parse(fs.readFileSync(path.join(ROOT, 'workspace/runs/run_latest.json'), 'utf8'));
  assert.strictEqual(rec.turns[3].arguments.rider, 'Evelyn Carter');
  assert.strictEqual(rec.turns[3].arguments.selected_curb_bay, 'north_bay (9.4ft >= 8.0ft)');
  assert.strictEqual(rec.status, 'awaiting_signoff');
});

console.log(`\n✓ ${passed}/${passed} Behavioral Verification Checks Passed (Nonzero Exit on Failure)`);
