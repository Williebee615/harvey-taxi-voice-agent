'use strict';
if (location.hostname.endsWith('.github.io')) location.replace(new URL('docs/', location.href));
const $ = id => document.getElementById(id);
let token = '', run = null, busy = false, automatic = false, connected = false;
const terminal = ['needs_input', 'awaiting_signoff', 'completed_after_human_signoff'];
function notice(message = '') { $('notice').textContent = message; }
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Console-Token':token},body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function syncButtons() {
  $('start').disabled = !connected || busy;
  const canContinue = run && run.status === 'paused' && !busy;
  $('next').disabled = !canContinue;
  $('all').disabled = !canContinue;
  $('stop').disabled = !automatic;
  $('btn-resume').disabled = !run || run.status !== 'awaiting_signoff' || busy;
  $('export').disabled = !run;
  $('send-followup').disabled = !run || run.requested_mode !== 'live' || !['needs_input','paused'].includes(run.status) || busy;
  $('history').disabled = busy;
  ['btn-safe','btn-unsafe','btn-incomplete','btn-return'].forEach(id => $(id).disabled = busy);
}
function appendText(parent, tag, text, cls) {
  const node = document.createElement(tag); node.textContent = text;
  if (cls) node.className = cls;
  parent.append(node); return node;
}
function render() {
  if (!run) return syncButtons();
  $('status').textContent = run.status.replaceAll('_',' ');
  $('turn-count').textContent = run.turn;
  $('fact-count').textContent = run.facts.length;
  $('tokens').textContent = run.receipts.reduce((sum,r) => sum + (r.usage.total_tokens || 0),0).toLocaleString();
  $('run-meta').textContent = `${run.run_id} · ${run.inference_mode} · curb: simulated fixture`;
  $('events').replaceChildren();
  for (const event of run.turns) {
    const box = document.createElement('article'); box.className = 'event';
    const head = document.createElement('div'); head.className = 'event-head';
    appendText(head,'span',event.turn,'number'); appendText(head,'strong',event.tool.replaceAll('_',' ')); box.append(head);
    const details = document.createElement('details'); appendText(details,'summary','Inspect tool arguments and observed evidence');
    appendText(details,'pre',JSON.stringify({arguments:event.arguments,result:event.observation,receipt:event.receipt},null,2)); box.append(details); $('events').append(box);
  }
  $('checks').replaceChildren();
  if (!Object.keys(run.verification).length) appendText($('checks'),'p','Checks have not run yet.','muted');
  for (const [name,check] of Object.entries(run.verification)) {
    const box = document.createElement('div'); if(!check.passed) box.className='failed';
    appendText(box,'b',`${check.passed?'✓':'!'} ${name.replaceAll('_',' ')}`);
    appendText(box,'small',check.reason || (check.missing_fields?.length ? check.missing_fields.join(', ') : check.contradiction ? 'Contradictory evidence detected' : 'Supplied evidence checked'));
    $('checks').append(box);
  }
  $('checklist').replaceChildren();
  for (const item of run.checklist) appendText($('checklist'),'div',item.question);
  $('memo').textContent = run.memo ? `Memo prepared before demo acknowledgment. Pending actions below describe that review stage.\n\n${run.memo.answer}\n\n` + run.memo.findings.map(f=>`${f.item}: ${f.finding} [${f.fact_ids.join(', ')}]`).join('\n\n') : 'A cited memo is required before sign-off.';
  if (run.memo?.pending_actions?.length) $('memo').textContent += '\n\nPending actions (not completed):\n' + run.memo.pending_actions.join('\n');
  if (run.memo?.limitations?.length) $('memo').textContent += '\n\nPrototype limitations:\n' + run.memo.limitations.join('\n');
  if (run.human_signoff_token) $('memo').textContent += `\n\nCurrent status: demo acknowledgment recorded by ${run.human_signoff_token} at ${run.signed_at}. Original memo retained as submitted. This is not authenticated dispatcher authorization; dispatch remains disabled.`;
  if (run.memo) $('memo').textContent += `\n\nRuntime provenance: ${run.inference_mode}; model invoked: ${Boolean(run.model_invoked_in_run)}; curb source: ${run.telemetry_source}.`;
  syncButtons();
}
async function perform(path, body) {
  busy = true; syncButtons(); notice('Working on one agent tool…');
  try { run = await api(path,body); render(); notice(run.pause_reason && run.status === 'paused' ? run.pause_reason : ''); }
  finally { busy = false; syncButtons(); }
}
async function continueRun(message='') {
  if (!run) return;
  await perform('/api/continue',{run_id:run.run_id,message});
}
async function runToPause() {
  automatic = true; syncButtons();
  try {
    let remaining = 39;
    while (automatic && run?.status === 'paused' && (!run.pause_reason || run.pause_reason === 'Turn batch exhausted; continue explicitly.') && remaining-- > 0) await continueRun();
    if (remaining <= 0) notice('Batch budget reached. Continue explicitly if more investigation is needed.');
  } finally { automatic=false; syncButtons(); await history(); }
}
async function history() {
  const runs = await api('/api/runs'); $('history').replaceChildren();
  const blank = document.createElement('option'); blank.value='';blank.textContent='Select a saved review';$('history').append(blank);
  for(const r of runs){const o=document.createElement('option');o.value=r.run_id;o.textContent=`${r.case} · ${r.status} · ${r.run_id.slice(-6)}`;$('history').append(o);}
}
function guarded(fn) {return async()=>{try{await fn();}catch(error){automatic=false;busy=false;notice(error.message);syncButtons();}};}
$('start').onclick=guarded(async()=>{automatic=false;await perform('/api/run',{case:$('case').value,mode:document.querySelector('input[name="execution-mode"]:checked').value,objective:$('objective').value||null});if(!$('step').checked&&!terminal.includes(run.status))await runToPause();await history();});
$('next').onclick=guarded(()=>continueRun());
$('all').onclick=guarded(runToPause);
$('stop').onclick=()=>{automatic=false;syncButtons();notice('Pausing after the current tool completes.');};
$('send-followup').onclick=guarded(async()=>{if(!$('followup').value.trim())throw new Error('Enter a follow-up first.');await continueRun($('followup').value);$('followup').value='';});
$('btn-resume').onclick=guarded(async()=>{if(!$('reviewer').value.trim())throw new Error('Enter your reviewer name first.');await perform('/api/approve',{run_id:run.run_id,signature:$('reviewer').value});await history();});
$('history').onchange=guarded(async()=>{if($('history').value){run=await api('/api/run?id='+encodeURIComponent($('history').value));render();}});
$('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(run,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=run.run_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
for(const [id,name] of [['btn-safe','healthcare-clinic-visit'],['btn-unsafe','harvey-taxi-unsafe-curb-boarding'],['btn-incomplete','harvey-taxi-incomplete-intake'],['btn-return','healthcare-missing-return-plan']])$(id).onclick=()=>{$('case').value=name;};
(async()=>{if(location.hostname.endsWith('.github.io'))return;try{const config=await api('/api/config');token=config.token;connected=true;$('connection').textContent='Local console connected';$('connection-dot').style.background='#218159';$('model-note').textContent=`${config.model} · Meta key ${config.key_configured?'configured (not yet verified)':'missing'}`;for(const name of config.cases){const o=document.createElement('option');o.value=name;o.textContent=name.replace('harvey-taxi-','').replaceAll('-',' ');$('case').append(o);}$('case').value='healthcare-clinic-visit';await history();}catch(error){$('connection').textContent='Local server required';notice('Start ./helper serve in Terminal, then open http://127.0.0.1:8765. This static page cannot run live inference.');}syncButtons();})();
