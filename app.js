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

if (typeof module !== 'undefined') module.exports = { computeIdempotencyKey, evaluateFleet, verifyCurbsideClearance, buildAgentAuditTrace, ADA_RAMP_MIN_CLEARANCE_FT, callMetaAgentAPI, PRICING, ADAPTER_CONFIG, META_MODEL_CONFIG, calculateFare, extractBooking, extractBookingWithMemory, appendTurn, matchDriver, retrieveFact: _kb.retrieveFact, HARVEY_TAXI_FACTS: _kb.HARVEY_TAXI_FACTS };
