'use strict';
if (location.hostname.endsWith('.github.io')) location.replace(new URL('docs/', location.href));
const $ = id => document.getElementById(id);
let token = '', run = null, busy = false, automatic = false, connected = false, caseImages = {}, listening = null;
// Browser speech recognition. This is not a Meta model; the page says so wherever speech is offered.
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
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
  ['btn-safe','btn-unsafe','btn-incomplete','btn-return','btn-card','btn-card-conflict'].forEach(id => $(id).disabled = busy);
  $('mic').disabled = busy || !Recognition;
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
    appendText(head,'span',event.turn,'number'); appendText(head,'strong',event.tool.replaceAll('_',' '));
    appendText(head,'small',event.receipt ? 'chosen by Meta model' : run.requested_mode === 'simulation' ? 'scripted simulation' : 'no model response','muted'); box.append(head);
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
  renderReceipts();
  if (run.memo) $('memo').textContent += `\n\nRuntime provenance: ${run.inference_mode}; model invoked: ${Boolean(run.model_invoked_in_run)}; curb source: ${run.telemetry_source}.`;
  syncButtons();
}
function renderReceipts() {
  const body = $('receipts'), status = $('exec-status'); body.replaceChildren();
  const failed = run.turns.filter(t => t.tool === 'api_error'), count = run.receipts.length;
  const failures = failed.length ? ` · ${failed.length} failed call${failed.length === 1 ? '' : 's'}` : '';
  if (run.requested_mode === 'simulation') { status.textContent = 'Offline simulation: scripted tool choices, no Meta API calls. Nothing in this run is model output.'; status.className = 'exec-status sim'; }
  else if (run.model_invoked_in_run) { status.textContent = `Live Meta API: ${count} successful response${count === 1 ? '' : 's'} from ${[...new Set(run.receipts.map(r => r.model))].join(', ')}${failures}`; status.className = 'exec-status live'; }
  else { status.textContent = `Live mode: no successful Meta response yet${failures}.`; status.className = 'exec-status sim'; }
  const rows = [...run.receipts.map(r => ({turn: r.turn, receipt: r})), ...failed.map(t => ({turn: t.turn, error: t.observation?.error || 'API error'}))].sort((a, b) => a.turn - b.turn);
  if (!rows.length) { const tr = document.createElement('tr'); appendText(tr,'td',run.requested_mode === 'simulation' ? 'No receipts: simulation makes no API calls.' : 'No API calls completed yet.').colSpan = 6; body.append(tr); return; }
  for (const row of rows) {
    const tr = document.createElement('tr'); appendText(tr,'td',row.turn);
    if (row.receipt) {
      const r = row.receipt, u = r.usage || {};
      appendText(tr,'td',r.status || 'completed'); appendText(tr,'td',r.model); appendText(tr,'td',r.response_id);
      appendText(tr,'td',`${u.input_tokens ?? u.prompt_tokens ?? '–'} / ${u.output_tokens ?? u.completion_tokens ?? '–'}`);
      appendText(tr,'td',r.latency_ms == null ? '–' : `${(r.latency_ms / 1000).toFixed(1)} s`);
    } else { tr.className = 'failed'; appendText(tr,'td','failed'); appendText(tr,'td',row.error).colSpan = 4; }
    body.append(tr);
  }
}
function updatePreview() {
  const card = (caseImages[$('case').value] || []).find(name => name.startsWith('appointment_card'));
  $('card-preview').hidden = !card;
  if (card) $('card-img').src = `/api/case-image?case=${encodeURIComponent($('case').value)}&name=${encodeURIComponent(card)}`;
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
$('start').onclick=guarded(async()=>{automatic=false;await perform('/api/run',{case:$('case').value,mode:document.querySelector('input[name="execution-mode"]:checked').value,objective:$('objective').value||null,spoken_request:$('spoken').value.trim()||null});if(!$('step').checked&&!terminal.includes(run.status))await runToPause();await history();});
$('next').onclick=guarded(()=>continueRun());
$('all').onclick=guarded(runToPause);
$('stop').onclick=()=>{automatic=false;syncButtons();notice('Pausing after the current tool completes.');};
$('send-followup').onclick=guarded(async()=>{if(!$('followup').value.trim())throw new Error('Enter a follow-up first.');await continueRun($('followup').value);$('followup').value='';});
$('btn-resume').onclick=guarded(async()=>{if(!$('reviewer').value.trim())throw new Error('Enter your reviewer name first.');await perform('/api/approve',{run_id:run.run_id,signature:$('reviewer').value});await history();});
$('history').onchange=guarded(async()=>{if($('history').value){run=await api('/api/run?id='+encodeURIComponent($('history').value));render();}});
$('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(run,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=run.run_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
for(const [id,name] of [['btn-safe','healthcare-clinic-visit'],['btn-unsafe','harvey-taxi-unsafe-curb-boarding'],['btn-incomplete','harvey-taxi-incomplete-intake'],['btn-return','healthcare-missing-return-plan'],['btn-card','healthcare-appointment-card'],['btn-card-conflict','healthcare-card-contradiction']])$(id).onclick=()=>{$('case').value=name;updatePreview();};
$('case').onchange=updatePreview;
if(!Recognition)$('speech-note').textContent='Speech recognition is not available in this browser. Type the request instead; it is handled the same way. (Browser speech recognition is not a Meta model.)';
$('mic').onclick=()=>{
  if(listening){listening.stop();return;}
  const recognizer=new Recognition(),before=$('spoken').value.trim();
  recognizer.lang='en-US';recognizer.interimResults=true;recognizer.continuous=false;
  recognizer.onresult=e=>{let text='';for(const result of e.results)text+=result[0].transcript;$('spoken').value=((before?before+' ':'')+text.trim()).slice(0,2000);};
  recognizer.onerror=e=>notice(`Speech recognition stopped (${e.error}). You can type the request instead.`);
  recognizer.onend=()=>{listening=null;$('mic').setAttribute('aria-pressed','false');$('mic').textContent='🎤 Speak request';};
  listening=recognizer;$('mic').setAttribute('aria-pressed','true');$('mic').textContent='■ Stop listening';recognizer.start();
};
(async()=>{if(location.hostname.endsWith('.github.io'))return;try{const config=await api('/api/config');token=config.token;connected=true;$('connection').textContent=config.hosting==='modal'?'Modal console connected':'Local console connected';$('connection-dot').style.background='#218159';$('model-note').textContent=`${config.model} · Meta key ${config.key_configured?'configured (not yet verified)':'missing'}`;for(const name of config.cases){const o=document.createElement('option');o.value=name;o.textContent=name.replace('harvey-taxi-','').replaceAll('-',' ');$('case').append(o);}caseImages=config.case_images||{};$('case').value='healthcare-clinic-visit';updatePreview();await history();}catch(error){$('connection').textContent='Local server required';notice('Start ./helper serve in Terminal, then open http://127.0.0.1:8765. This static page cannot run live inference.');}syncButtons();})();
