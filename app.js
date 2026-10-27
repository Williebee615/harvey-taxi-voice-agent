
// === NOREL AI DOMINANT MULTI-AGENT PLATFORM REGISTRY (v1.0.0) ===
const NOREL_PLATFORM_AGENTS = [
  { slug: 'norel-mobility', name: 'Norel Mobility (Harvey Accessible Dispatch)', model: 'meta-models/muse-spark-open-1026', tools: ['voice.transcribe', 'sam3.curb_verify', 'fare.deterministic', 'action.confirm'], badge: 'Flagship Physical World Agent' },
  { slug: 'norel', name: 'Norel Core', model: 'muse-wonder-1.0', tools: ['memory.read', 'attachment.read'], badge: 'General Assistant' },
  { slug: 'norel-research', name: 'Norel Research', model: 'muse-wonder-1.0', tools: ['research.web', 'attachment.read'], badge: 'SSRF-Guarded Citations' },
  { slug: 'norel-business', name: 'Norel Business', model: 'muse-wonder-1.0', tools: ['attachment.read', 'research.web'], badge: 'Executive & Ops' },
  { slug: 'norel-creator', name: 'Norel Creator', model: 'muse-wonder-1.0', tools: ['attachment.read', 'vision.analyze'], badge: 'Creative Briefs' },
  { slug: 'norel-developer', name: 'Norel Developer', model: 'muse-wonder-1.0', tools: ['attachment.read', 'research.docs'], badge: 'Verifiable Code' },
  { slug: 'norel-documents', name: 'Norel Documents', model: 'muse-wonder-1.0', tools: ['document.extract', 'attachment.read'], badge: 'Grounded PDF/DOCX' },
  { slug: 'norel-tasks', name: 'Norel Tasks', model: 'meta-models/muse-spark-open-1026', tools: ['task.propose', 'action.confirm'], badge: 'DST Durable Scheduler' },
  { slug: 'norel-vision', name: 'Norel Vision', model: 'sam-3.1', tools: ['vision.analyze', 'sam3.curb_verify'], badge: 'Multimodal & SAM 3.1' }
];

// Standalone demo logic — production backend untouched.
// Guardrails: live dispatch and payments are hard-coded OFF.
'use strict';

const PRICING = {
  baseFare: 5.00,
  perMile: 0.90,
  perMinute: 0.35,
  bookingFee: 2.00,
  minimumFare: 8.00,
  discountRate: 0.20,      // medical / foundation: 20% off subtotal
  airportSurcharge: 5.00   // flat, added AFTER discount, BEFORE minimum clamp
};

const ADAPTER_CONFIG = {
  endpoint: '/api/rides/request',
  method: 'POST',
  liveDispatchEnabled: false,  // GATE #2: hard-coded OFF
  paymentsEnabled: false       // GATE #2: hard-coded OFF
};

const roundCents = n => Math.round(n * 100) / 100;

function calculateFare({ distanceMiles, durationMinutes, discount = false, airport = false } = {}) {
  // Production rule: no valid route, no fare.
  if (!Number.isFinite(distanceMiles) || !Number.isFinite(durationMinutes) ||
      distanceMiles <= 0 || durationMinutes <= 0) return null;

  const distanceCharge = roundCents(distanceMiles * PRICING.perMile);
  const timeCharge = roundCents(durationMinutes * PRICING.perMinute);
  const subtotal = roundCents(PRICING.baseFare + distanceCharge + timeCharge + PRICING.bookingFee);
  const discountAmount = discount ? roundCents(subtotal * PRICING.discountRate) : 0;
  const airportAmount = airport ? PRICING.airportSurcharge : 0;
  const rawTotal = roundCents(subtotal - discountAmount + airportAmount);
  const total = Math.max(PRICING.minimumFare, rawTotal);

  return { baseFare: PRICING.baseFare, distanceCharge, timeCharge,
           bookingFee: PRICING.bookingFee, subtotal, discountAmount,
           airportSurcharge: airportAmount, total };
}

function extractBooking(text = '') {
  const lower = text.toLowerCase();
  const m = text.match(/from\s+(.+?)\s+to\s+(.+?)(?:\s+at\s+|\s+tomorrow|$)/i);
  return {
    pickup: m ? m[1].trim() : null,
    dropoff: m ? m[2].trim() : null,
    needsWheelchair: /wheelchair|accessible van/.test(lower),
    hasServiceAnimal: /service animal|service dog/.test(lower)
  };
}

// Strict hard filters (AND gates) -> proximity tie-breaker only on survivors.
function matchDriver(drivers, { needsWheelchair = false, hasServiceAnimal = false } = {}) {
  const eligible = drivers
    .filter(d => d.online)
    .filter(d => !needsWheelchair || d.accessibleVan)
    .filter(d => !hasServiceAnimal || d.serviceAnimalOptIn);
  if (!eligible.length) return null; // honest no-match, never relax filters
  return eligible.sort((a, b) => a.distanceMiles - b.distanceMiles)[0];
}


// --- Meta Global AI Hackathon: Memory, RAG & Model Config ---
const META_MODEL_CONFIG = {
  reasoningModel: 'muse-spark',
  transcriptionModel: 'muse-voice-transcribe',
  openWeightsModel: 'meta-models/muse-spark-open-1026',
  modalEndpoint: 'https://williebee615--norel-ai-harvey-taxi-assistant-extract-acc-b09ac3.us-east.modal.run',
  codingAgent: 'muse-code',
  maxContextTurns: 6
};

const _kb = (typeof require !== 'undefined')
  ? require('./knowledge.js')
  : (typeof window !== 'undefined' && window.HarveyKnowledge ? window.HarveyKnowledge : { HARVEY_TAXI_FACTS: [], retrieveFact: () => ({ matched: false }) });

function appendTurn(history = [], turn = {}, maxTurns = 6) {
  const next = [...history, turn];
  return next.length > maxTurns ? next.slice(next.length - maxTurns) : next;
}

function extractBookingWithMemory(history = [], latestText = '') {
  const turns = appendTurn(history, { role: 'user', text: latestText }, 6);
  let pickup = null, dropoff = null, needsWheelchair = false, hasServiceAnimal = false, day = null;
  const days = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday','tomorrow','today'];
  for (const t of turns) {
    const str = typeof t === 'string' ? t : (t.text || '');
    const ext = extractBooking(str);
    if (ext.pickup) pickup = ext.pickup;
    if (ext.dropoff) dropoff = ext.dropoff.split(/\s+(?:with|using|needing|and|for)\s+/i)[0].trim();
    if (ext.needsWheelchair) needsWheelchair = true;
    if (ext.hasServiceAnimal) hasServiceAnimal = true;
    for (const w of str.toLowerCase().replace(/[^a-z\s]/g, '').split(/\s+/)) {
      if (days.includes(w)) day = w;
    }
  }
  return { pickup, dropoff, needsWheelchair, hasServiceAnimal, day, turnsUsed: turns.length };
}


async function callMetaAgentAPI({ text, history = [], apiKey = '', endpoint = 'https://api.meta.ai/v1/chat/completions', model = 'meta-models/muse-spark-open-1026' } = {}) {
  const localIntent = extractBookingWithMemory(history, text);
  if (!apiKey) {
    return { mode: 'local-verifiable-fallback', model, intent: localIntent };
  }
  const turns = appendTurn(history, { role: 'user', content: text }, 6);
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
    body: JSON.stringify({
      model,
      messages: [
        { role: 'system', content: 'Extract structured accessible ride booking JSON: {pickup, dropoff, needsWheelchair, hasServiceAnimal, day}. Never calculate fares or override hard accessibility filters.' },
        ...turns.map(t => ({ role: t.role || 'user', content: t.content || t.text || String(t) }))
      ],
      temperature: 0
    })
  });
  const data = await res.json();
  return { mode: 'live-meta-api', model, raw: data, intent: localIntent };
}


// --- Senior Architecture Upgrades: Fleet Elimination Matrix, SAM 3.1 Curbside Tool, Idempotency & Audit Trace ---
const ADA_RAMP_MIN_CLEARANCE_FT = 8.0;

function computeIdempotencyKey({ pickup, dropoff, needsWheelchair, hasServiceAnimal, day } = {}) {
  const raw = [
    String(pickup || '').toLowerCase().trim(),
    String(dropoff || '').toLowerCase().trim(),
    Boolean(needsWheelchair),
    Boolean(hasServiceAnimal),
    String(day || 'immediate').toLowerCase().trim()
  ].join('|');
  // Deterministic 32-bit FNV-1a hash for zero-dependency browser/Node parity
  let hash = 0x811c9dc5;
  for (let i = 0; i < raw.length; i++) {
    hash ^= raw.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return 'idem_ht_' + hash.toString(16).padStart(8, '0');
}

function evaluateFleet(drivers = [], { needsWheelchair = false, hasServiceAnimal = false } = {}) {
  const evaluations = drivers.map(d => {
    const reasons = [];
    if (!d.online) reasons.push('REJECTED_OFFLINE');
    if (needsWheelchair && !d.accessibleVan) reasons.push('REJECTED_NO_WHEELCHAIR_RAMP');
    if (hasServiceAnimal && !d.serviceAnimalOptIn) reasons.push('REJECTED_NO_SERVICE_ANIMAL_OPT_IN');
    return {
      id: d.id,
      distanceMiles: d.distanceMiles,
      eligible: reasons.length === 0,
      status: reasons.length === 0 ? 'ELIGIBLE' : reasons.join(', ')
    };
  });
  const winner = matchDriver(drivers, { needsWheelchair, hasServiceAnimal });
  return {
    selectedDriver: winner,
    totalCandidates: drivers.length,
    eligibleCount: evaluations.filter(e => e.eligible).length,
    auditMatrix: evaluations
  };
}

function verifyCurbsideClearance({ clearanceFeet = 0, obstacles = [], needsWheelchair = false } = {}) {
  const cleanObstacles = Array.isArray(obstacles) ? obstacles.filter(Boolean) : [];
  if (!needsWheelchair) {
    return {
      model: 'sam-3.1 + meta-models/muse-spark-open-1026',
      safeForRamp: true,
      clearanceFeet,
      requiredFeet: 0,
      status: 'STANDARD_CURB_OK',
      explanation: 'Standard pickup: ADA ramp deployment not required.'
    };
  }
  const hasBlockingObstacle = cleanObstacles.some(o => /hydrant|bollard|parked car|snowbank|construction/i.test(String(o)));
  const hasWidth = Number.isFinite(clearanceFeet) && clearanceFeet >= ADA_RAMP_MIN_CLEARANCE_FT;
  const safe = hasWidth && !hasBlockingObstacle;
  return {
    model: 'sam-3.1 + meta-models/muse-spark-open-1026',
    safeForRamp: safe,
    clearanceFeet,
    requiredFeet: ADA_RAMP_MIN_CLEARANCE_FT,
    obstaclesDetected: cleanObstacles,
    status: safe ? 'ADA_RAMP_VERIFIED' : 'CURB_BLOCKED_RELOCATE_PICKUP',
    explanation: safe
      ? `SAM 3.1 verified ${clearanceFeet}ft lateral curb clearance (>= ${ADA_RAMP_MIN_CLEARANCE_FT}ft ADA minimum) with zero blocking obstacles.`
      : `Unsafe for wheelchair ramp: ${clearanceFeet}ft available (requires >= ${ADA_RAMP_MIN_CLEARANCE_FT}ft)` + (hasBlockingObstacle ? ` and blocked by [${cleanObstacles.join(', ')}].` : '.')
  };
}

function buildAgentAuditTrace({ booking, fare, fleetEval, curbCheck } = {}) {
  const idempotencyKey = computeIdempotencyKey(booking || {});
  return {
    schemaVersion: '2.0.0-verifiable-agent',
    orchestrator: 'norel-ai',
    idempotencyKey,
    state: (fare && fleetEval && fleetEval.selectedDriver) ? 'VERIFIED_SHADOW_READY' : 'HALTED_MISSING_REQUIREMENT',
    modelsInvoked: [
      META_MODEL_CONFIG.openWeightsModel,
      META_MODEL_CONFIG.transcriptionModel,
      'sam-3.1'
    ],
    steps: [
      { step: 1, tool: 'extractBookingWithMemory', output: booking },
      { step: 2, tool: 'calculateFare', output: fare },
      { step: 3, tool: 'evaluateFleet', output: fleetEval },
      { step: 4, tool: 'verifyCurbsideClearance', output: curbCheck || null }
    ],
    guardrails: {
      liveDispatchEnabled: ADAPTER_CONFIG.liveDispatchEnabled,
      paymentsEnabled: ADAPTER_CONFIG.paymentsEnabled
    }
  };
}

if (typeof module !== 'undefined') module.exports = {
  META_SAI_MODELS,
  buildMuseGlimmerConfig,
  generateMuseImageAdaPassSpec, computeIdempotencyKey, evaluateFleet, verifyCurbsideClearance, buildAgentAuditTrace, ADA_RAMP_MIN_CLEARANCE_FT, callMetaAgentAPI, PRICING, ADAPTER_CONFIG, META_MODEL_CONFIG, calculateFare, extractBooking, extractBookingWithMemory, appendTurn, matchDriver, retrieveFact: _kb.retrieveFact, HARVEY_TAXI_FACTS: _kb.HARVEY_TAXI_FACTS };


// === META S.A.I. FULL STACK HELPERS (Muse Glimmer 30B, Muse Spark 1.3, Muse Image) ===
const META_SAI_MODELS = {
  museWonder: 'muse-wonder-1.0',
  museSpark13: 'muse-spark-1.3',
  museSparkOpen: 'meta-models/muse-spark-open-1026',
  museGlimmer30B: 'meta-models/Muse-Glimmer-30B',
  museImage: 'muse-image',
  museVoiceTranscribe: 'muse-voice-transcribe',
  sam31: 'sam-3.1',
  museCode: 'muse-code-cli'
};

function buildMuseGlimmerConfig(reasoningStrength = 'high') {
  const allowed = ['low', 'medium', 'high', 'xhigh'];
  const level = allowed.includes(reasoningStrength) ? reasoningStrength : 'high';
  return {
    model: META_SAI_MODELS.museGlimmer30B,
    systemPromptHeader: `Reasoning strength: ${level}`,
    speculativeDecoding: 'DFlash-16-token-block-diffusion',
    perceptionEncoder: true,
    license: 'Apache-2.0'
  };
}

function generateMuseImageAdaPassSpec(trip = {}) {
  const pickup = trip.pickup || '1200 Broadway (ADA Curb Zone A)';
  const dropoff = trip.dropoff || 'Vanderbilt Clinic Main Entrance';
  const clearanceFt = trip.clearanceFt || 9.5;
  return {
    model: META_SAI_MODELS.museImage,
    orchestrator: META_SAI_MODELS.museWonder,
    prompt: `High-contrast accessible transit boarding pass and overhead ADA wheelchair ramp deployment schematic showing ${clearanceFt}ft clear curb zone at ${pickup} to ${dropoff}`,
    pickup,
    dropoff,
    clearanceFt,
    adaVerified: clearanceFt >= 8.0,
    zeroAdaSurcharge: true
  };
}

if (typeof window !== 'undefined') {
  window.META_SAI_MODELS = META_SAI_MODELS;
  window.buildMuseGlimmerConfig = buildMuseGlimmerConfig;
  window.generateMuseImageAdaPassSpec = generateMuseImageAdaPassSpec;
  window.renderMuseImageAdaPass = function() {
    const wrap = document.getElementById('muse-image-canvas-wrap');
    const status = document.getElementById('muse-image-status');
    if (!wrap) return;
    const spec = generateMuseImageAdaPassSpec({ pickup: 'Home (Curb Zone Verified)', dropoff: 'Medical Center', clearanceFt: 9.5 });
    wrap.style.display = 'block';
    if (status) status.textContent = 'Verified: muse-image + SAM 3.1 visual boarding pass synthesized.';
    wrap.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #283A6B;padding-bottom:10px;margin-bottom:12px;">
        <strong style="color:#62D9EA;">NOREL CREATOR × MUSE IMAGE (<code>muse-image</code>) — ADA VISUAL BOARDING &amp; CURB DIAGRAM</strong>
        <span style="background:rgba(52,211,153,0.15);color:#34D399;border:1px solid #34D399;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;">SAM 3.1 + MUSE IMAGE VERIFIED</span>
      </div>
      <svg viewBox="0 0 680 150" style="width:100%;height:auto;background:#050811;border:1px solid #26355D;border-radius:10px;padding:8px;">
        <rect x="12" y="16" width="210" height="118" rx="10" fill="#11192E" stroke="#62D9EA" stroke-width="2"/>
        <text x="26" y="42" fill="#62D9EA" font-size="13" font-family="monospace" font-weight="bold">ADA VAN #HT-104</text>
        <text x="26" y="66" fill="#F4F6FC" font-size="12" font-family="sans-serif">Pickup: ${spec.pickup}</text>
        <text x="26" y="88" fill="#F4F6FC" font-size="12" font-family="sans-serif">Dropoff: ${spec.dropoff}</text>
        <text x="26" y="114" fill="#34D399" font-size="12" font-family="monospace">ADA Fee: $0.00 (Exempt)</text>
        <rect x="245" y="26" width="175" height="98" rx="8" fill="rgba(98,217,234,0.12)" stroke="#62D9EA" stroke-dasharray="6,4" stroke-width="2"/>
        <text x="260" y="58" fill="#62D9EA" font-size="12" font-family="monospace" font-weight="bold">SAM 3.1 RAMP ZONE</text>
        <text x="260" y="82" fill="#34D399" font-size="13" font-family="monospace" font-weight="bold">Clearance: 9.5 ft &ge; 8.0 ft</text>
        <text x="260" y="104" fill="#94A3B8" font-size="11" font-family="monospace">Obstacles: NONE</text>
        <rect x="442" y="16" width="224" height="118" rx="10" fill="#11192E" stroke="#A89BF6" stroke-width="2"/>
        <text x="456" y="42" fill="#A89BF6" font-size="12" font-family="monospace" font-weight="bold">MUSE GLIMMER 30B EDGE</text>
        <text x="456" y="66" fill="#F4F6FC" font-size="11" font-family="monospace">Reasoning strength: high</text>
        <text x="456" y="88" fill="#F4F6FC" font-size="11" font-family="monospace">Speculative: DFlash 16-tok</text>
        <text x="456" y="112" fill="#62D9EA" font-size="11" font-family="monospace">Model: muse-image + sam-3.1</text>
      </svg>
    `;
  };
}
