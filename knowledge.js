// 11 verified Harvey Taxi Service facts for grounded RAG (keyword scoring, zero hallucination)
const HARVEY_TAXI_FACTS = [
  { id: 'base-fare', keywords: ['base', 'fare', 'start', 'initial', 'cost'], answer: 'The base fare is $5.00, plus $0.90 per mile, $0.35 per minute, and a $2.00 booking fee.', source: 'app.js:calculateFare' },
  { id: 'minimum-fare', keywords: ['minimum', 'min', 'short', 'lowest'], answer: 'Every ride has an $8.00 minimum fare. No fare is quoted without a valid route.', source: 'app.js:calculateFare' },
  { id: 'discount', keywords: ['discount', 'medical', 'foundation', 'clinic', 'senior'], answer: 'Eligible medical and foundation rides receive a 20% discount off the subtotal before any airport surcharge.', source: 'app.js:calculateFare' },
  { id: 'airport', keywords: ['airport', 'surcharge', 'flight', 'terminal'], answer: 'Airport trips include a flat $5.00 surcharge applied after any subtotal discount.', source: 'app.js:calculateFare' },
  { id: 'wheelchair', keywords: ['wheelchair', 'accessible', 'van', 'ramp', 'mobility'], answer: 'Wheelchair-accessible requests apply a strict hard filter for ramp-equipped vans before ranking by distance.', source: 'app.js:matchDriver' },
  { id: 'service-animal', keywords: ['service', 'animal', 'dog', 'guide', 'pet'], answer: 'Riders with service animals are strictly matched only with drivers who have explicitly opted in to carry service animals.', source: 'app.js:matchDriver' },
  { id: 'no-match', keywords: ['unavailable', 'no driver', 'relax', 'fallback', 'wait'], answer: 'If no online driver meets all accessibility and service-animal filters, the system returns an honest no-match rather than sending an ineligible vehicle.', source: 'app.js:matchDriver' },
  { id: 'safety', keywords: ['safety', 'zero-tolerance', 'policy', 'background', 'trust'], answer: 'Harvey Taxi enforces a strict zero-tolerance safety and non-discrimination policy across all fleet operations.', source: 'policy/safety' },
  { id: 'voice-booking', keywords: ['voice', 'speak', 'mic', 'read-aloud', 'blind', 'screen'], answer: 'Riders can book by voice using Meta Muse Voice Transcribe / Web Speech API and hear full fare and driver explanations read aloud.', source: 'index.html' },
  { id: 'guardrails', keywords: ['dispatch', 'payment', 'charge', 'live', 'sandbox'], answer: 'In this standalone demo, live dispatch and payment charging are hard-coded OFF behind a single POST /api/rides/request adapter seam.', source: 'app.js:ADAPTER_CONFIG' },
  { id: 'support', keywords: ['contact', 'support', 'email', 'help', 'dispatch'], answer: 'For live fleet dispatch support or assisted booking review, contact Harvey Taxi Service at williebee@harveytaxiservice.com.', source: 'config/contact' }
];

function retrieveFact(query = '') {
  const words = String(query).toLowerCase().replace(/[^a-z0-9\s-]/g, '').split(/\s+/).filter(Boolean);
  if (!words.length) return { matched: false, answer: 'Please ask a specific question about Harvey Taxi fares, accessibility, or policies.', source: null };

  let best = null;
  let bestScore = 0;
  for (const fact of HARVEY_TAXI_FACTS) {
    const score = fact.keywords.reduce((acc, kw) => acc + (words.includes(kw) ? 1 : 0), 0);
    if (score > bestScore) {
      bestScore = score;
      best = fact;
    }
  }

  if (!best || bestScore === 0) {
    return {
      matched: false,
      answer: 'I do not have a verified Harvey Taxi policy note for that question. I only answer from verified company facts.',
      source: null
    };
  }
  return { matched: true, id: best.id, answer: best.answer, source: best.source, score: bestScore };
}

if (typeof module !== 'undefined') module.exports = { HARVEY_TAXI_FACTS, retrieveFact };
if (typeof window !== 'undefined') window.HarveyKnowledge = { HARVEY_TAXI_FACTS, retrieveFact };
