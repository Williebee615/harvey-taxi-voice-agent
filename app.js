'use strict';
if (location.hostname.endsWith('.github.io')) location.replace(new URL('docs/', location.href));
const $ = id => document.getElementById(id);
let token = '', run = null, busy = false, automatic = false, connected = false, caseImages = {}, recorder = null, transcription = null;
// Meta speech-to-text: the browser records only after a click, encodes 16 kHz mono WAV and posts it to
// this console's server, which holds the Meta key. The browser never sees the key.
const canRecord = Boolean(navigator.mediaDevices?.getUserMedia && (window.AudioContext || window.webkitAudioContext));
const MAX_RECORD_SECONDS = 60, WAV_RATE = 16000;
const terminal = ['needs_input', 'awaiting_signoff', 'completed_after_human_signoff'];
// The chosen mode is remembered across refreshes; a live review still starts only when the user clicks Start.
const MODE_KEY = 'harvey.executionMode';
function selectedMode() { return document.querySelector('input[name="execution-mode"]:checked').value; }
function restoreMode() {
  let saved = null;
  try { saved = localStorage.getItem(MODE_KEY); } catch (error) {}
  if (saved === 'live' || saved === 'simulation') $(`mode-${saved}`).checked = true;
  showMode();
}
function rememberMode() {
  try { localStorage.setItem(MODE_KEY, selectedMode()); } catch (error) {}
  showMode();
}
function showMode() {
  const live = selectedMode() === 'live', arrow = document.createElement('span'); arrow.textContent = '↗';
  $('start').replaceChildren(live ? 'Start live Meta review (paid API calls) ' : 'Start offline simulation (no API calls) ', arrow);
  $('paid-note').hidden = !live;
}
function notice(message = '') { $('notice').textContent = message; }
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Console-Token':token},body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) {
    // The server restarted since this page loaded. Nothing was sent; fetch a fresh token and let the user click again.
    if (data.code === 'session_expired') {
      try { token = (await (await fetch('/api/config')).json()).token; } catch (error) {}
      throw new Error('The console restarted since this page loaded. Nothing was sent and no Meta call was made. Click the button again.');
    }
    if (data.code === 'transcript_expired') clearTranscription('This Meta transcript can no longer be used (already used, expired, or the console restarted). Record the request again.');
    throw new Error(data.error || `Request failed (${response.status})`);
  }
  return data;
}
function syncButtons() {
  $('start').disabled = !connected || busy || Boolean(recorder) || (transcription && !$('confirm-transcript').checked);
  const canContinue = run && run.status === 'paused' && !busy;
  $('next').disabled = !canContinue;
  $('all').disabled = !canContinue;
  $('stop').disabled = !automatic;
  $('btn-resume').disabled = !run || run.status !== 'awaiting_signoff' || busy;
  $('export').disabled = !run;
  $('send-followup').disabled = !run || run.requested_mode !== 'live' || !['needs_input','paused'].includes(run.status) || busy;
  $('history').disabled = busy;
  ['btn-safe','btn-unsafe','btn-incomplete','btn-return','btn-card','btn-card-conflict'].forEach(id => $(id).disabled = busy);
  $('mic').disabled = !connected || (busy && !recorder) || !canRecord;
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
  $('run-meta').textContent = `Run ${run.run_id}`;
  renderProvenance();
  renderBadges();
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
    if (name === 'curb_check') appendText($('checks'),'p','🟠 SIMULATED CURB MEASUREMENTS — Demonstration data, not camera measurements','badge sim');
    appendText(box,'b',`${check.passed?'✓':'!'} ${name.replaceAll('_',' ')}${name==='curb_check'?' (simulated measurements)':''}`);
    appendText(box,'small',check.reason || (check.missing_fields?.length ? check.missing_fields.join(', ') : check.contradiction ? 'Contradictory evidence detected' : 'Supplied evidence checked'));
    $('checks').append(box);
  }
  $('checklist').replaceChildren();
  for (const item of run.checklist) appendText($('checklist'),'div',item.question);
  $('memo').textContent = run.memo ? `Memo prepared before demo acknowledgment. Pending actions below describe that review stage.\n\n${run.memo.answer}\n\n` + run.memo.findings.map(f=>`${f.item}: ${f.finding} [${f.fact_ids.join(', ')}]`).join('\n\n') : 'A cited memo is required before sign-off.';
  if (run.memo?.pending_actions?.length) $('memo').textContent += '\n\nPending actions (not completed):\n' + run.memo.pending_actions.join('\n');
  if (run.memo?.limitations?.length) $('memo').textContent += '\n\nPrototype limitations:\n' + run.memo.limitations.join('\n');
  if (run.human_signoff_token) $('memo').textContent += `\n\nCurrent status: human acknowledgment recorded by ${run.human_signoff_token} at ${run.signed_at}. Original memo retained as submitted. No vehicle was dispatched and no payment was authorized; this is not authenticated dispatcher authorization.`;
  renderReceipts();
  if (run.memo) $('memo').textContent += `\n\nProvenance: reasoning ${run.model_invoked_in_run ? 'by live Meta model' : 'scripted (offline simulation)'}; curb measurements from a simulated fixture, not measured by any model.`;
  syncButtons();
}
// Headline labels. Response IDs are recorded from Meta's replies; this console does not authenticate them with Meta.
function inferenceBadge() {
  const recorded = run.receipts.filter(r => r.response_id), models = [...new Set(recorded.map(r => r.model))].join(', ');
  if (run.requested_mode === 'simulation') return ['OFFLINE SIMULATION — NO META API CALLS', 'Scripted tool choices; nothing in this run is model output.', 'sim'];
  if (run.model_invoked_in_run && recorded.length) return [`🟢 LIVE META INFERENCE — ${recorded.length} RECORDED RESPONSE${recorded.length === 1 ? '' : 'S'}`, `${models} · response IDs recorded by this console, not independently authenticated with Meta`, 'live'];
  return ['LIVE MODE — NO META RESPONSE RECORDED YET', 'No successful Meta response yet; nothing in this run is model output so far.', 'none'];
}
function renderBadges() {
  const [title, detail, kind] = inferenceBadge(), badge = $('inference-badge');
  badge.replaceChildren(title); appendText(badge, 'small', detail); badge.className = `badge ${kind}`; badge.hidden = false;
  const signoff = $('signoff-badge'); signoff.hidden = !run.human_signoff_token;
  if (run.human_signoff_token) { signoff.replaceChildren('🔵 HUMAN ACKNOWLEDGMENT RECORDED — No vehicle dispatched'); appendText(signoff, 'small', `By ${run.human_signoff_token} at ${run.signed_at}. No payment authorized.`); }
}
// Each kind of evidence has its own source; a live Meta review can still use simulated curb measurements.
function provenanceRows() {
  const live = run.requested_mode === 'live', count = run.receipts.length, speech = run.speech_source, card = run.card_extraction;
  const final = ['needs_input', 'awaiting_signoff', 'completed_after_human_signoff'].includes(run.status), integrity = run.run_integrity || {};
  const reasoning = !live ? ['Offline simulation: scripted tool choices, no model', 'sim']
    : run.model_invoked_in_run ? [`Live Meta inference: ${count} response${count === 1 ? '' : 's'} from ${[...new Set(run.receipts.map(r => r.model))].join(', ')}`, 'live']
    : ['Live mode: no successful Meta response yet', 'sim'];
  const spoken = !run.run_documents?.['spoken_request.txt'] ? ['No spoken request in this run', 'none']
    : speech && typeof speech === 'object' ? [`Meta ${speech.model} transcript, session ${speech.session_id}${speech.confirmed_by_reviewer ? ', confirmed by the reviewer' : ''}`, 'live']
    : ['Typed text (not Meta speech-to-text)', 'sim'];
  const cardRow = !card ? [(caseImages[run.case] || []).length ? 'Card not read yet' : 'No appointment card in this case', 'none']
    : card.extracted_by === 'LIVE_META_API' ? ['Read from the image by the live Meta model; fields cross-checked by code', 'live']
    : ['Scripted fixture values (offline simulation); no model read the image', 'sim'];
  const integrityRow = !final ? ['Checked when the run reaches needs input or awaiting sign-off', 'none']
    : integrity.state === run.status && integrity.passed ? [`Consistent for ${run.status.replaceAll('_', ' ')} (record check, not a booking approval)`, 'live']
    : integrity.state ? [`Problem: ${(integrity.errors || []).join('; ')}`, 'warn']
    : integrity.passed ? ['Passed the earlier memo-acceptance check (saved by an earlier version of the console)', 'live']
    : ['Not recorded: this run was saved by an earlier version, which only checked runs that reached sign-off', 'none'];
  return [['Reasoning', ...reasoning], ['Spoken request', ...spoken], ['Appointment card', ...cardRow],
          ['Curb measurements', 'Simulated fixture: not measured by a camera, SAM or any model', 'sim'], ['Audit integrity', ...integrityRow]];
}
function renderProvenance() {
  $('provenance').replaceChildren();
  for (const [label, text, kind] of provenanceRows()) {
    const row = document.createElement('div'); row.className = `prov-${kind}`;
    appendText(row, 'dt', label); appendText(row, 'dd', text); $('provenance').append(row);
  }
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
$('start').onclick=guarded(async()=>{automatic=false;const spoken=transcription?{transcription_id:transcription.transcription_id,transcript_confirmed:$('confirm-transcript').checked}:{spoken_request:$('spoken').value.trim()||null};clearTranscription();await perform('/api/run',{case:$('case').value,mode:selectedMode(),objective:$('objective').value||null,...spoken});if(!$('step').checked&&!terminal.includes(run.status))await runToPause();await history();});
$('next').onclick=guarded(()=>continueRun());
$('all').onclick=guarded(runToPause);
$('stop').onclick=()=>{automatic=false;syncButtons();notice('Pausing after the current tool completes.');};
$('send-followup').onclick=guarded(async()=>{if(!$('followup').value.trim())throw new Error('Enter a follow-up first.');await continueRun($('followup').value);$('followup').value='';});
$('btn-resume').onclick=guarded(async()=>{if(!$('reviewer').value.trim())throw new Error('Enter your reviewer name first.');await perform('/api/approve',{run_id:run.run_id,signature:$('reviewer').value});await history();});
$('history').onchange=guarded(async()=>{if($('history').value){run=await api('/api/run?id='+encodeURIComponent($('history').value));render();}});
$('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(run,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=run.run_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
for(const [id,name] of [['btn-safe','healthcare-clinic-visit'],['btn-unsafe','harvey-taxi-unsafe-curb-boarding'],['btn-incomplete','harvey-taxi-incomplete-intake'],['btn-return','healthcare-missing-return-plan'],['btn-card','healthcare-appointment-card'],['btn-card-conflict','healthcare-card-contradiction']])$(id).onclick=()=>{$('case').value=name;updatePreview();};
$('case').onchange=updatePreview;
document.querySelectorAll('input[name="execution-mode"]').forEach(input => input.onchange = rememberMode);
restoreMode();
function clearTranscription(note='') {
  transcription = null; $('confirm-transcript').checked = false; $('confirm-row').hidden = true;
  $('speech-meta').hidden = !note; $('speech-meta').textContent = note; syncButtons();
}
function showRecording(text, busyState) {
  $('rec-indicator').hidden = !text; $('rec-text').textContent = text || ''; $('rec-indicator').classList.toggle('busy', Boolean(busyState));
}
function encodeWav(chunks, rate) {
  // Downsample to 16 kHz by averaging, then write 16-bit little-endian mono PCM in a RIFF/WAVE container.
  const input = new Float32Array(chunks.reduce((n, c) => n + c.length, 0)); let at = 0;
  for (const c of chunks) { input.set(c, at); at += c.length; }
  const ratio = rate / WAV_RATE, length = Math.floor(input.length / ratio), view = new DataView(new ArrayBuffer(44 + length * 2));
  const text = (offset, value) => { for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i)); };
  text(0, 'RIFF'); view.setUint32(4, 36 + length * 2, true); text(8, 'WAVE'); text(12, 'fmt ');
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true); view.setUint32(24, WAV_RATE, true);
  view.setUint32(28, WAV_RATE * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true); text(36, 'data'); view.setUint32(40, length * 2, true);
  for (let i = 0; i < length; i++) {
    let sum = 0, count = 0;
    for (let j = Math.floor(i * ratio); j < Math.min(input.length, Math.floor((i + 1) * ratio)); j++) { sum += input[j]; count++; }
    const sample = Math.max(-1, Math.min(1, count ? sum / count : 0));
    view.setInt16(44 + i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return new Blob([view], {type: 'audio/wav'});
}
async function startRecording() {
  clearTranscription();
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true}}); }
  catch (error) { notice(error.name === 'NotAllowedError' ? 'Microphone permission was denied. Allow it in the browser, or type the request instead.' : 'No microphone is available. Type the request instead.'); return; }
  const context = new (window.AudioContext || window.webkitAudioContext)(), source = context.createMediaStreamSource(stream);
  const node = context.createScriptProcessor(4096, 1, 1), chunks = [], started = Date.now();
  node.onaudioprocess = e => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  source.connect(node); node.connect(context.destination);
  const timer = setInterval(() => {
    const seconds = Math.floor((Date.now() - started) / 1000);
    $('rec-time').textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
    if (seconds >= MAX_RECORD_SECONDS) stopRecording();
  }, 250);
  recorder = {stream, context, node, source, chunks, timer};
  $('mic').setAttribute('aria-pressed', 'true'); $('mic').textContent = '■ Stop and transcribe with Meta';
  $('rec-time').textContent = '0:00'; showRecording('Mic on · recording'); notice('Recording. Click Stop when you have finished speaking.'); syncButtons();
}
async function stopRecording() {
  if (!recorder) return;
  const {stream, context, node, source, chunks, timer} = recorder; recorder = null;
  clearInterval(timer); node.disconnect(); source.disconnect(); stream.getTracks().forEach(t => t.stop());
  const rate = context.sampleRate; await context.close();
  $('mic').setAttribute('aria-pressed', 'false'); $('mic').textContent = '🎤 Record with Meta speech-to-text';
  const wav = encodeWav(chunks, rate);
  if (wav.size <= 44 + WAV_RATE * 2 * 0.3) { showRecording(''); notice('The recording was too short. Try again.'); syncButtons(); return; }
  busy = true; showRecording('Microphone off. Transcribing with Meta…', true); notice('Sending the recording to Meta speech-to-text through this console\'s server…'); syncButtons();
  try {
    const response = await fetch('/api/transcribe', {method: 'POST', headers: {'Content-Type': 'audio/wav', 'X-Console-Token': token}, body: wav});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Transcription failed (${response.status})`);
    transcription = data; $('spoken').value = data.transcript;
    $('speech-meta').textContent = `Transcribed by Meta ${data.model} · session ${data.session_id} · ${((data.audio_duration_ms || 0) / 1000).toFixed(1)} s audio · est. $${(data.cost_usd_estimate || 0).toFixed(4)}. Check it, then confirm below. Editing the text turns it into typed text, not a Meta transcript.`;
    $('speech-meta').hidden = false; $('confirm-row').hidden = false; $('confirm-transcript').checked = false;
    notice('Meta transcript ready. Confirm it matches what you said before starting the review.');
  } catch (error) { notice(error.message + ' You can type the request instead.'); }
  finally { busy = false; showRecording(''); syncButtons(); }
}
if (!canRecord) $('speech-note').textContent = 'This browser cannot record audio here. Type the request instead; it is checked the same way but labeled as typed text, not Meta.';
$('mic').onclick = guarded(async () => { if (recorder) await stopRecording(); else await startRecording(); });
$('confirm-transcript').onchange = syncButtons;
$('spoken').oninput = () => { if (transcription) clearTranscription('Edited: this will be submitted as typed text, not as a Meta transcript.'); };
(async()=>{if(location.hostname.endsWith('.github.io'))return;try{const config=await api('/api/config');token=config.token;connected=true;$('connection').textContent=config.hosting==='modal'?'Modal console connected':'Local console connected';$('connection-dot').style.background='#218159';$('model-note').textContent=`${config.model} · Meta key ${config.key_configured?'configured (not yet verified)':'missing'}`;for(const name of config.cases){const o=document.createElement('option');o.value=name;o.textContent=name.replace('harvey-taxi-','').replaceAll('-',' ');$('case').append(o);}caseImages=config.case_images||{};$('case').value='healthcare-clinic-visit';updatePreview();await history();}catch(error){$('connection').textContent='Local server required';notice('Start ./helper serve in Terminal, then open http://127.0.0.1:8765. This static page cannot run live inference.');}syncButtons();})();
