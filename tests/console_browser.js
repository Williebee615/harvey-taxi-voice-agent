// Headless check of the console's mode memory and headline labels. Every /api request is answered
// locally from fixtures, so no server, key or Meta call is involved. Usage: node console_browser.js <repo>
const fs = require('fs'), path = require('path');
const {chromium} = require('playwright');
const root = process.argv[2];
const live = JSON.parse(fs.readFileSync(path.join(root, 'docs/evidence/hosted-console-2026-10-29/run_b2023b2da615466fba74a611b17ec923.json')));
const sim = {...live, run_id: 'run_sim', requested_mode: 'simulation', inference_mode: 'DETERMINISTIC_FALLBACK_SIMULATION', model_invoked_in_run: false,
  receipts: [], turns: live.turns.map(t => ({...t, receipt: null})), human_signoff_token: null, signed_at: null, authorization_mode: 'NONE', status: 'awaiting_signoff'};
const runs = {[live.run_id]: live, run_sim: sim};
const files = {'/': ['index.html', 'text/html'], '/app.js': ['app.js', 'text/javascript'], '/console.css': ['console.css', 'text/css']};

(async () => {
  const browser = await chromium.launch(), page = await browser.newPage(), posts = [], out = {};
  let configCalls = 0, tokenGeneration = 1;
  await page.route('http://console.test/**', route => {
    const url = new URL(route.request().url());
    if (route.request().method() === 'POST') posts.push(url.pathname);
    if (files[url.pathname]) return route.fulfill({contentType: files[url.pathname][1], body: fs.readFileSync(path.join(root, files[url.pathname][0]))});
    const json = body => route.fulfill({contentType: 'application/json', body: JSON.stringify(body)});
    if (url.pathname === '/api/run' && route.request().method() === 'POST')
      return route.fulfill({status: 403, contentType: 'application/json', body: JSON.stringify({error: 'Console session expired. Nothing was sent.', code: 'session_expired'})});
    if (url.pathname === '/api/config') { configCalls++; return json({token: `t${tokenGeneration}`, hosting: 'local', model: 'muse-spark-1.3', key_configured: true, cases: ['healthcare-clinic-visit'], case_images: {}}); }
    if (url.pathname === '/api/runs') return json(Object.values(runs).map(r => ({run_id: r.run_id, case: r.case, status: r.status})));
    if (url.pathname === '/api/run') return json(runs[url.searchParams.get('id')]);
    return route.fulfill({status: 404, contentType: 'application/json', body: '{"error":"not in fixture"}'});
  });
  const state = async () => page.evaluate(() => ({live: document.getElementById('mode-live').checked, start: document.getElementById('start').textContent,
    paidHidden: document.getElementById('paid-note').hidden, badge: document.getElementById('inference-badge').hidden ? null : document.getElementById('inference-badge').textContent,
    signoff: document.getElementById('signoff-badge').hidden ? null : document.getElementById('signoff-badge').textContent, checks: document.getElementById('checks').textContent}));
  const ready = () => page.waitForFunction(() => document.getElementById('connection').textContent.includes('connected'));
  await page.goto('http://console.test/'); await ready();
  out.initial = await state();
  await page.check('#mode-live');
  await page.reload(); await ready();
  out.afterReload = await state();
  await page.selectOption('#history', live.run_id); await page.waitForFunction(() => !document.getElementById('inference-badge').hidden);
  out.liveRun = await state();
  await page.selectOption('#history', 'run_sim'); await page.waitForFunction(() => document.getElementById('inference-badge').textContent.includes('OFFLINE'));
  out.simRun = await state();
  await page.check('#mode-simulation'); await page.reload(); await ready();
  out.backToSimulation = await state();
  out.posts = [...posts];
  // A restarted server rejects the old token: the page refreshes it, says nothing was sent, and does not retry.
  const before = configCalls; tokenGeneration = 2;
  await page.click('#start'); await page.waitForFunction(() => document.getElementById('notice').textContent.includes('restarted'));
  out.expired = {notice: await page.textContent('#notice'), configRefetched: configCalls - before, runPosts: posts.filter(p => p === '/api/run').length,
    startEnabled: await page.isEnabled('#start')};
  console.log(JSON.stringify(out));
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
