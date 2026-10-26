'use strict';
const assert = require('node:assert');
const { PRICING, ADAPTER_CONFIG, META_MODEL_CONFIG, calculateFare, extractBooking, extractBookingWithMemory, appendTurn, matchDriver, retrieveFact, HARVEY_TAXI_FACTS } = require('../app.js');
let n = 0;
const test = (name, fn) => { fn(); n++; console.log(`ok ${n} - ${name}`); };

const DRIVERS = [
  { id: 'close-ineligible', online: true,  accessibleVan: false, serviceAnimalOptIn: false, distanceMiles: 0.5 },
  { id: 'far-eligible',     online: true,  accessibleVan: true,  serviceAnimalOptIn: true,  distanceMiles: 3.0 },
  { id: 'mid-eligible',     online: true,  accessibleVan: true,  serviceAnimalOptIn: true,  distanceMiles: 1.5 },
  { id: 'offline-nearest',  online: false, accessibleVan: true,  serviceAnimalOptIn: true,  distanceMiles: 0.1 }
];

// Extraction (5)
test('extracts pickup and dropoff', () => { const b = extractBooking('Book a ride from Home to Clinic'); assert.equal(b.pickup, 'Home'); assert.equal(b.dropoff, 'Clinic'); });
test('detects wheelchair need', () => assert.equal(extractBooking('from Home to Clinic, I need a wheelchair van').needsWheelchair, true));
test('detects service animal', () => assert.equal(extractBooking('from Home to Clinic with my service animal').hasServiceAnimal, true));
test('no wheelchair flag when absent', () => assert.equal(extractBooking('from Home to Clinic').needsWheelchair, false));
test('missing route yields null dropoff', () => assert.equal(extractBooking('book me a ride please').dropoff, null));

// Pricing (8)
test('10.0mi/20min standard = $23.00', () => assert.equal(calculateFare({ distanceMiles: 10, durationMinutes: 20 }).total, 23.00));
test('1.0mi/2min standard = $8.60', () => assert.equal(calculateFare({ distanceMiles: 1, durationMinutes: 2 }).total, 8.60));
test('0.5mi/1min clamps to $8.00 minimum', () => assert.equal(calculateFare({ distanceMiles: 0.5, durationMinutes: 1 }).total, 8.00));
test('no valid distance -> no fare', () => assert.equal(calculateFare({ distanceMiles: 0, durationMinutes: 20 }), null));
test('no valid duration -> no fare', () => assert.equal(calculateFare({ distanceMiles: 10, durationMinutes: 0 }), null));
test('discount: 10mi/20min = $23.00 - $4.60 = $18.40', () => assert.equal(calculateFare({ distanceMiles: 10, durationMinutes: 20, discount: true }).total, 18.40));
test('airport: 10mi/20min = $23.00 + $5.00 = $28.00', () => assert.equal(calculateFare({ distanceMiles: 10, durationMinutes: 20, airport: true }).total, 28.00));
test('combined: $23.00 - $4.60 + $5.00 = $23.40', () => assert.equal(calculateFare({ distanceMiles: 10, durationMinutes: 20, discount: true, airport: true }).total, 23.40));

// Matching (6)
test('offline drivers excluded', () => assert.notEqual(matchDriver(DRIVERS, {}).id, 'offline-nearest'));
test('non-accessible van excluded when wheelchair needed', () => assert.notEqual(matchDriver(DRIVERS, { needsWheelchair: true }).id, 'close-ineligible'));
test('non-opted-in driver excluded for service animal', () => assert.notEqual(matchDriver(DRIVERS, { hasServiceAnimal: true }).id, 'close-ineligible'));
test('farther eligible beats closer ineligible', () => assert.equal(matchDriver(DRIVERS, { needsWheelchair: true, hasServiceAnimal: true }).id, 'mid-eligible'));
test('nearest eligible wins', () => assert.equal(matchDriver(DRIVERS, {}).id, 'close-ineligible'));
test('honest no-match when no eligible driver', () => assert.equal(matchDriver([{ id: 'x', online: true, accessibleVan: false, serviceAnimalOptIn: false, distanceMiles: 1 }], { needsWheelchair: true }), null));

// Guardrails / adapter (3)
test('live dispatch hard-coded OFF', () => assert.equal(ADAPTER_CONFIG.liveDispatchEnabled, false));
test('payments hard-coded OFF', () => assert.equal(ADAPTER_CONFIG.paymentsEnabled, false));
test('single adapter seam: POST /api/rides/request', () => { assert.equal(ADAPTER_CONFIG.method, 'POST'); assert.equal(ADAPTER_CONFIG.endpoint, '/api/rides/request'); });


// Memory & Grounded RAG (5)
test('memory: rolling context window caps at 6 turns', () => {
  let h = [];
  for (let i = 1; i <= 8; i++) h = appendTurn(h, { role: 'user', text: 'turn ' + i }, 6);
  assert.equal(h.length, 6);
  assert.equal(h[0].text, 'turn 3');
});
test('memory: follow-up turn preserves pickup/dropoff and updates day to wednesday', () => {
  const h = [{ role: 'user', text: 'Book a ride from Home to Clinic with a wheelchair van' }];
  const res = extractBookingWithMemory(h, 'Actually change it to Wednesday and add my service dog');
  assert.equal(res.pickup, 'Home');
  assert.equal(res.dropoff, 'Clinic');
  assert.equal(res.needsWheelchair, true);
  assert.equal(res.hasServiceAnimal, true);
  assert.equal(res.day, 'wednesday');
});
test('RAG: 11 verified Harvey Taxi facts loaded', () => assert.equal(HARVEY_TAXI_FACTS.length, 11));
test('RAG: answers base fare question from verified facts', () => {
  const r = retrieveFact('What is the base fare?');
  assert.equal(r.matched, true);
  assert.equal(r.id, 'base-fare');
});
test('RAG: refuses to hallucinate on unknown topic', () => {
  const r = retrieveFact('Do you offer helicopter flights to Mars?');
  assert.equal(r.matched, false);
});

test('Meta Hackathon model config uses meta-models/muse-spark-open-1026 & muse-voice-transcribe', () => {
  assert.equal(META_MODEL_CONFIG.openWeightsModel, 'meta-models/muse-spark-open-1026');
  assert.equal(META_MODEL_CONFIG.transcriptionModel, 'muse-voice-transcribe');
});

console.log(`\n${n}/28 checks passed`);
console.log('PRICING constants:', PRICING);
