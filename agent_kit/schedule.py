"""Deterministic cross-check of dates and times a rider speaks against the booking and appointment card.

The transcript is untrusted evidence. Code, not the model, reads the dates and times in it. Anything it
cannot pin down exactly (a weekday without a date, "tomorrow", an unlabeled or approximate time, a slash
date that could be read two ways, two different dates, another time zone, vague phrases such as "in the
afternoon") is ambiguous and asks the rider to clarify; anything that disagrees with the booking, the card
or itself is a conflict. Either stops the review at needs_input.

Year rule: a date spoken without a year takes the booking's year (the intake appointment date, else the
pickup date). A spoken year is used as said. No other inference is made, so across a year boundary a
date that differs from the booking is reported as a conflict, never moved to a neighbouring year.
Times are compared as wall-clock times in the booking's own time zone; times are never converted.
"""
from __future__ import annotations
import re
from datetime import date

MONTHS = {name: i for i, names in enumerate([('january', 'jan'), ('february', 'feb'), ('march', 'mar'), ('april', 'apr'),
          ('may',), ('june', 'jun'), ('july', 'jul'), ('august', 'aug'), ('september', 'sep', 'sept'), ('october', 'oct'),
          ('november', 'nov'), ('december', 'dec')], 1) for name in names}
WEEKDAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
UNITS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9}
TEENS = {'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16,
         'seventeen': 17, 'eighteen': 18, 'nineteen': 19}
TENS = {'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50}
ORDINALS = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5, 'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9,
            'tenth': 10, 'eleventh': 11, 'twelfth': 12, 'thirteenth': 13, 'fourteenth': 14, 'fifteenth': 15, 'sixteenth': 16,
            'seventeenth': 17, 'eighteenth': 18, 'nineteenth': 19, 'twentieth': 20, 'thirtieth': 30}
RELATIVE = re.compile(r'\b(day after tomorrow|today|tonight|tomorrow|yesterday|next week|this week|next (?:%s)|this (?:%s))\b' % ('|'.join(WEEKDAYS), '|'.join(WEEKDAYS)))
ZONES = re.compile(r'\b(eastern|pacific|mountain|central|alaska|hawaii)(?: standard| daylight)?(?: time)?\b|\b(est|edt|pst|pdt|mst|mdt|cst|cdt|utc|gmt)\b')
CENTRAL = {'central', 'cst', 'cdt'}
ZONE_OF = {'America/Chicago': CENTRAL}
APPROX = ('around', 'about', 'approximately', 'roughly', 'after', 'ish')
VAGUE = re.compile(r'\b(day after tomorrow|in (?:a|one|two|three|four|five|\d+) (?:days?|weeks?)|(?:next|this|last) (?:weekend|month)|end of (?:the )?(?:week|month)|weekend'
                   r'|(?:early|late|mid) (?:morning|afternoon|evening|day)|morning|afternoon|evening|midday ish|lunch ?time|lunch|as soon as possible|asap|soon|sometime|whenever|am or pm'
                   r'|(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d{1,2})ish)\b')
GREETING = re.compile(r'\bgood (morning|afternoon|evening)\b')
ROLES = (('arrive_by', re.compile(r'\b(arrive|arrival|be there|get there|get me there|there by|in by)\b')),
         ('pickup', re.compile(r'\b(pick (?:me )?up|pickup|picked up|leave|leaving|depart)\b')),
         ('appointment', re.compile(r'\b(appointment|appt|scheduled|visit is|see the doctor)\b')))


def _normalize(text):
    text = text.lower().replace('-', ' ').replace("o'clock", ' oclock').replace('o clock', ' oclock')
    text = re.sub(r'\b([ap])\.\s?m\.', r'\1m', text)
    text = re.sub(r'\b([ap]) m\b', r'\1m', text)
    return re.sub(r'[^a-z0-9:/ ]+', ' ', text)


def _number(words):
    """Parse a cardinal or ordinal of up to two words ('twenty first', 'forty five', 'second'). Returns (value, used)."""
    if not words:
        return None, 0
    first, second = words[0], words[1] if len(words) > 1 else ''
    if first in TENS:
        tail = UNITS.get(second) or {k: v for k, v in ORDINALS.items() if v < 10}.get(second)
        return (TENS[first] + tail, 2) if tail else (TENS[first], 1)
    for table in (UNITS, TEENS, ORDINALS):
        if first in table:
            return table[first], 1
    match = re.fullmatch(r'(\d{1,2})(st|nd|rd|th)?', first)
    return (int(match[1]), 1) if match else (None, 0)


def _dates(words, year):
    """Explicit calendar dates. Returns (dates, day_only_mentions, ambiguous_notes, consumed word indexes)."""
    found, day_only, notes, used, assumed = [], [], [], set(), set()
    for i, word in enumerate(words):
        if word in MONTHS:
            day, n = _number(words[i + 1:i + 3])
            span = range(i, i + 1 + n)
            if day is None and i >= 2 and words[i - 1] == 'of':  # "the second of November", "the twenty first of May"
                for width in (2, 1):
                    value, m = _number(words[i - 1 - width:i - 1]) if i - 1 - width >= 0 else (None, 0)
                    if value is not None and m == width:
                        day, n, span = value, 0, range(i - 1 - width, i + 1)
                        break
            if day is None:
                notes.append(f"'{word}' without a day")
                continue
            explicit = words[i + 1 + n] if i + 1 + n < len(words) and re.fullmatch(r'20\d\d', words[i + 1 + n]) else None
            try:
                found.append(date(int(explicit) if explicit else year, MONTHS[word], day))
                if not explicit:
                    assumed.add(found[-1])
            except (TypeError, ValueError):
                notes.append(f"'{word} {day}' is not a valid date")
            used.update(span)
            if explicit:
                used.add(i + 1 + n)
    for i, word in enumerate(words):
        if i in used:
            continue
        iso = re.fullmatch(r'(20\d\d)/(\d{1,2})/(\d{1,2})', word) or re.fullmatch(r'(20\d\d)(\d{2})(\d{2})', word)
        slash = re.fullmatch(r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?', word)
        if iso:
            try:
                found.append(date(int(iso[1]), int(iso[2]), int(iso[3])))
            except ValueError:
                notes.append(f"'{word}' is not a valid date")
            used.add(i)
        elif slash:
            a, b = int(slash[1]), int(slash[2])
            if a <= 12 and b <= 12 and a != b:
                notes.append(f"'{word}' could be month/day or day/month")
            else:
                try:
                    found.append(date(year if not slash[3] else int(slash[3]) % 100 + 2000, a, b) if a <= 12 else date(year, b, a))
                    if not slash[3]:
                        assumed.add(found[-1])
                except (TypeError, ValueError):
                    notes.append(f"'{word}' is not a valid date")
            used.add(i)
        elif re.fullmatch(r'\d{1,2}(st|nd|rd|th)', word) or (word in ORDINALS and (i == 0 or words[i - 1] in ('the', 'on'))):
            day_only.append(_number([word])[0])
            used.add(i)
    return found, day_only, notes, used, assumed


def _times(words, skip):
    """Spoken clock times with the role the rider gave them. Each candidate list holds every 24-hour reading."""
    out, consumed, i = [], set(), 0
    while i < len(words):
        if i in skip:
            i += 1
            continue
        word, start, hour, minute, n = words[i], i, None, 0, 0
        clock = re.fullmatch(r'(\d{1,2}):(\d{2})', word)
        if word in ('noon', 'midday', 'midnight'):
            start = i - 1 if i > 0 and words[i - 1] == 'twelve' else i
            fixed = '12:00' if word != 'midnight' else '00:00'
            context = ' '.join(words[max(0, start - 6):start])
            role = next((name for name, pattern in ROLES if pattern.search(context)), 'unlabeled')
            out.append({'role': role, 'spoken': ' '.join(words[start:i + 1]), 'candidates': [fixed],
                        'approximate': start > 0 and words[start - 1] in APPROX})
            consumed.update(range(start, i + 1))
            i += 1
            continue
        if clock:
            hour, minute, n = int(clock[1]), int(clock[2]), 1
        elif word in ('half', 'quarter') and i + 2 < len(words) and words[i + 1] in ('past', 'to'):
            base, used = _number(words[i + 2:i + 3])
            if base and 1 <= base <= 12:
                minute = 30 if word == 'half' else 15
                hour, n = (base, 3) if words[i + 1] == 'past' else (base - 1 or 12, 3)
                minute = minute if words[i + 1] == 'past' else 60 - minute
        else:
            value, used = _number([word]) if word in UNITS or word in TEENS or re.fullmatch(r'\d{1,2}', word) else (None, 0)
            if value is not None and 1 <= value <= 12:
                rest = words[i + 1:i + 3]
                if rest[:1] == ['oclock']:
                    hour, n = value, 2
                elif rest[:1] == ['oh'] and len(rest) > 1 and rest[1] in UNITS:
                    hour, minute, n = value, UNITS[rest[1]], 3
                else:
                    mins, m = _number(rest) if rest and (rest[0] in TENS or rest[0] in TEENS or re.fullmatch(r'\d{2}', rest[0])) else (None, 0)
                    if mins is not None and 0 <= mins <= 59:
                        hour, minute, n = value, mins, 1 + m
                    elif i > 0 and words[i - 1] in ('at', 'by', 'around', 'before', 'after', 'about'):
                        hour, n = value, 1
        if hour is None or n == 0:
            i += 1
            continue
        after = ' '.join(words[i + n:i + n + 4])
        am, pm = re.match(r'(am|in the morning|this morning)\b', after), re.match(r'(pm|in the (?:afternoon|evening)|tonight)\b', after)
        meridiem, suffix = ('am', am[1]) if am else ('pm', pm[1]) if pm else (None, '')
        if not meridiem and not clock and n == 1 and words[i - 1:i] not in (['at'], ['by'], ['around'], ['before'], ['after'], ['about']):
            i += 1
            continue  # a bare number such as "two" in "two bags" is not a time
        if meridiem == 'am':
            candidates = [hour % 12]
        elif meridiem == 'pm':
            candidates = [hour % 12 + 12]
        elif hour > 12 or hour == 0 or (clock and int(clock[1]) >= 13):
            candidates = [hour]
        else:
            candidates = sorted({hour % 12, hour % 12 + 12})
        context = ' '.join(words[max(0, start - 6):start])
        role = next((name for name, pattern in ROLES if pattern.search(context)), 'unlabeled')
        approximate = (start > 0 and words[start - 1] in APPROX) or words[i + n:i + n + 1] == ['ish']
        out.append({'role': role, 'spoken': ' '.join(words[start:i + n] + suffix.split()), 'candidates': [f'{h:02d}:{minute:02d}' for h in candidates],
                    'approximate': approximate})
        consumed.update(range(start, i + n + len(suffix.split())))
        i += n
    return out, consumed


def _clock(value):
    match = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', value or '')
    return (date.fromisoformat(match[1]), match[2]) if match else (None, None)


def _zone(value):
    match = re.search(r'\d{2}:\d{2}\s+([A-Za-z]+/[A-Za-z_]+)', value or '')
    return match[1] if match else None


def check(text, intake, card_fields=None):
    """Compare spoken dates and times with the rider intake and, when one was read in this run, the appointment card."""
    card_fields = card_fields or {}
    appt_date, appt_time = _clock(intake.get('Appointment Time', ''))
    pickup_date, pickup_time = _clock(intake.get('Pickup Time', ''))
    booking_date = appt_date or pickup_date
    words = _normalize(text).split()
    conflicts, clarify = [], []
    dates, day_only, notes, used, assumed = _dates(words, booking_date.year if booking_date else None)
    times, timed = _times(words, used)
    weekdays = [w for w in words if w in WEEKDAYS]
    relative = sorted(set(RELATIVE.findall(_normalize(text))))
    leftover = GREETING.sub(' ', ' '.join(w for k, w in enumerate(words) if k not in used and k not in timed))
    vague = sorted({m.group(0) for m in VAGUE.finditer(RELATIVE.sub(' ', leftover))})
    zones = sorted({(m[1] or m[2]) for m in ZONES.finditer(' '.join(words))})
    booking_zone = _zone(intake.get('Appointment Time', '')) or _zone(intake.get('Pickup Time', ''))
    spoken = {'dates': [d.isoformat() for d in dates], 'weekdays': weekdays, 'times': times, 'relative': relative,
              'vague': vague, 'time_zones': zones, 'year_rule': 'A date spoken without a year takes the booking year; a spoken year is used as said'}
    if not (dates or day_only or notes or times or weekdays or relative or vague or zones):
        return {'passed': True, 'status': 'no_schedule_spoken', 'spoken': spoken, 'conflicts': [], 'clarify': [],
                'reason': 'No date or time was spoken; the booking times come from the written intake'}
    clarify += [f'Confirm the date: {note}' for note in notes]
    clarify += [f"Confirm the calendar date meant by '{r}'" for r in relative]
    clarify += [f"Confirm the exact date and time meant by '{v}'" for v in vague]
    foreign = [zone for zone in zones if zone not in ZONE_OF.get(booking_zone, set())]
    for zone in foreign:
        clarify.append(f"The rider mentioned {zone.upper() if len(zone) <= 3 else zone.title()} time; booking times are in {booking_zone or 'an unstated time zone'}. Confirm the time in the booking's time zone")
    if len({d for d in dates}) > 1:
        clarify.append('More than one date was spoken: ' + ', '.join(sorted({d.isoformat() for d in dates})))
    if dates and booking_date is None:
        clarify.append('The intake has no booking date to compare with the spoken date')
    references = [('booking', appt_date)] + ([('appointment card', date.fromisoformat(card_fields['appointment_date']))] if card_fields.get('appointment_date') else [])
    for spoken_date in sorted(set(dates)):
        for label, ref in references:
            if ref and spoken_date != ref:
                said = (f"{spoken_date:%B} {spoken_date.day} (no year spoken; the booking year {spoken_date.year} is used)"
                        if spoken_date in assumed else spoken_date.isoformat())
                conflicts.append(f'Spoken date {said} differs from the {label} date {ref.isoformat()}')
        for day in weekdays:
            if WEEKDAYS[spoken_date.weekday()] != day:
                conflicts.append(f'Rider said {day.title()}, but {spoken_date.isoformat()} is a {WEEKDAYS[spoken_date.weekday()].title()}')
    for day in day_only:
        if not any(d.day == day for d in dates):
            clarify.append(f'Confirm the month for the day {day} the rider mentioned')
    if weekdays and not dates:
        clarify.append(f"Confirm the calendar date meant by '{weekdays[0].title()}'")
    arrive_ref = card_fields.get('arrive_by')
    appt_refs = {t for t in (appt_time, card_fields.get('appointment_time')) if t}
    for spoken_time in times:
        options, role, said = spoken_time['candidates'], spoken_time['role'], spoken_time['spoken']
        if foreign:
            continue  # a time in another zone is not compared; the rider is asked to restate it
        if spoken_time['approximate']:
            clarify.append(f"Confirm an exact time instead of the approximate '{said}'")
            continue
        if role == 'appointment':
            if appt_refs and not any(all(o == r for r in appt_refs) for o in options):
                conflicts.append(f"Spoken appointment time '{said}' differs from the booked appointment time {', '.join(sorted(appt_refs))}")
            elif not appt_refs:
                clarify.append(f"No booked appointment time to compare with '{said}'")
        elif role == 'pickup':
            if pickup_time and pickup_time not in options:
                conflicts.append(f"Spoken pickup time '{said}' differs from the booked pickup time {pickup_time}")
            elif not pickup_time:
                clarify.append(f"No booked pickup time to compare with '{said}'")
        elif role == 'arrive_by':
            if arrive_ref:
                if arrive_ref not in options:
                    conflicts.append(f"Spoken arrive-by time '{said}' differs from the card's arrive-by time {arrive_ref}")
            elif pickup_time and appt_time:
                if not any(pickup_time < o <= appt_time for o in options):
                    conflicts.append(f"Spoken arrive-by time '{said}' is not between the booked pickup {pickup_time} and appointment {appt_time}")
            else:
                clarify.append(f"No booked times to compare with the arrive-by time '{said}'")
        else:
            known = {t for t in (pickup_time, appt_time, arrive_ref, card_fields.get('appointment_time')) if t}
            if not known.intersection(options):
                clarify.append(f"Confirm whether '{said}' is the pickup, arrival or appointment time")
    # The rider's own times must also agree with each other: pickup before arrival, arrival no later than the appointment.
    exact = [t for t in times if not t['approximate'] and not foreign]
    by_role = {role: [t for t in exact if t['role'] == role] for role in ('pickup', 'arrive_by', 'appointment')}
    for earlier, later, rule in (('pickup', 'arrive_by', lambda a, b: a < b), ('arrive_by', 'appointment', lambda a, b: a <= b),
                                 ('pickup', 'appointment', lambda a, b: a < b)):
        for first in by_role[earlier]:
            for second in by_role[later]:
                pairs = (zip(first['candidates'], second['candidates']) if len(first['candidates']) == len(second['candidates']) == 2
                         else [(a, b) for a in first['candidates'] for b in second['candidates']])
                if not any(rule(a, b) for a, b in pairs):
                    conflicts.append(f"The rider's {earlier.replace('_', '-')} time '{first['spoken']}' conflicts with their {later.replace('_', '-')} time '{second['spoken']}'")
    status = 'conflict' if conflicts else 'ambiguous' if clarify else 'matches'
    reason = ('Spoken dates and times agree with the booking' + (' and the appointment card' if card_fields else '') if status == 'matches'
              else '; '.join(conflicts + [f'Ask the rider: {c}' for c in clarify]) + '. Request clarification from the rider before booking.')
    return {'passed': status == 'matches', 'status': status, 'spoken': spoken, 'conflicts': conflicts, 'clarify': clarify,
            'compared_with': {'appointment': appt_date.isoformat() + ' ' + appt_time if appt_date else None,
                              'pickup': pickup_date.isoformat() + ' ' + pickup_time if pickup_date else None,
                              'card': {k: card_fields.get(k) for k in ('appointment_date', 'appointment_time', 'arrive_by') if card_fields.get(k)} or None},
            'reason': reason}
