"""Spoken dates and times are checked by code against the intake and the appointment card. Offline only."""
import json
import unittest
from pathlib import Path
from agent_kit import schedule
from test_agent import AgentFixture

ROOT = Path(__file__).resolve().parent.parent
INTAKE = {'Appointment Time': '2026-11-02 10:00 America/Chicago', 'Pickup Time': '2026-11-02 09:00 America/Chicago'}
CARD = {'appointment_date': '2026-11-02', 'appointment_time': '10:00', 'arrive_by': '09:45'}
DEMO = ('Hi, this is Jordan Ellis. I need a wheelchair accessible ride with my service dog to Demo Community Clinic '
        'on Monday, November second. I need to arrive by nine forty-five in the morning.')


def status(text, card=None):
    return schedule.check(text, INTAKE, card)['status']


class ScheduleParsingTests(unittest.TestCase):
    def test_matching_inputs(self):
        for text, card in [(DEMO, CARD), (DEMO, None),
                           ('Ride on the second of November; arrive by 9:45 am.', CARD),
                           ('My appointment is at ten o\'clock on Nov 2 2026.', CARD),
                           ('Please pick me up at nine on November 2nd.', None),
                           ('I need to be there by quarter to ten.', CARD),
                           ('Ride on 2026/11/02.', None)]:
            with self.subTest(text=text):
                self.assertEqual(status(text, card), 'matches', schedule.check(text, INTAKE, card)['reason'])

    def test_meta_transcript_of_the_demo_clip_matches(self):
        """The real Meta transcript from the 2026-10-29 batch, with its repeated '2nd' and '9 45'."""
        record = json.loads((ROOT / 'docs/evidence/live-batch-2026-10-29/run_1f9f09924a9c46ea9f6e2f3fe1319216.json').read_text())
        transcript = record['run_documents']['spoken_request.txt']
        self.assertIn('9 45', transcript)
        result = schedule.check(transcript, INTAKE)
        self.assertEqual(result['status'], 'matches', result['reason'])
        self.assertEqual(result['spoken']['dates'], ['2026-11-02']); self.assertEqual(result['spoken']['times'][0]['candidates'], ['09:45'])

    def test_conflicting_inputs(self):
        cases = {'Ride on Tuesday, November third.': 'differs from the booking date 2026-11-02',
                 'Ride on Monday, November third.': 'Rider said Monday, but 2026-11-03 is a Tuesday',
                 'My appointment is at 2 pm.': 'differs from the booked appointment time 10:00',
                 'Pick me up at half past eight.': 'differs from the booked pickup time 09:00',
                 'I need to arrive by 10:30.': 'not between the booked pickup 09:00 and appointment 10:00',
                 'I need to arrive by nine thirty.': "differs from the card's arrive-by time 09:45"}
        for text, message in cases.items():
            with self.subTest(text=text):
                result = schedule.check(text, INTAKE, CARD if 'nine thirty' in text else None)
                self.assertEqual(result['status'], 'conflict'); self.assertFalse(result['passed'])
                self.assertIn(message, result['reason']); self.assertIn('Request clarification from the rider', result['reason'])
        card_says_third = {**CARD, 'appointment_date': '2026-11-03'}
        self.assertIn('appointment card date 2026-11-03', schedule.check('Ride on November second.', INTAKE, card_says_third)['reason'])

    def test_ambiguous_inputs_ask_for_clarification(self):
        cases = {'Ride on Monday please.': "date meant by 'Monday'",
                 'I need a ride tomorrow.': "date meant by 'tomorrow'",
                 'Ride next Friday.': "date meant by 'next friday'",
                 'Ride on 11/2.': 'could be month/day or day/month',
                 'Ride on November 2 or November 4.': 'More than one date was spoken',
                 'See you at 3 pm.': 'pickup, arrival or appointment time',
                 'Ride in November.': "'november' without a day",
                 'Ride on November 31.': 'not a valid date'}
        for text, message in cases.items():
            with self.subTest(text=text):
                result = schedule.check(text, INTAKE)
                self.assertFalse(result['passed']); self.assertTrue(result['clarify'])
                self.assertIn(message, result['reason']); self.assertIn('Ask the rider', result['reason'])

    def test_no_schedule_spoken_is_neutral(self):
        for text in ['I need a wheelchair accessible van.', 'I have two bags and one service dog.']:
            with self.subTest(text=text):
                self.assertEqual(status(text), 'no_schedule_spoken')
                self.assertTrue(schedule.check(text, INTAKE)['passed'])

    def test_missing_booking_date_cannot_confirm(self):
        self.assertEqual(schedule.check('Ride on November second.', {})['status'], 'ambiguous')


class ScheduleReviewTests(AgentFixture):
    def test_review_stops_for_conflicting_or_ambiguous_speech(self):
        for text, expected in [('I need a wheelchair ride with my service dog on Tuesday, November third.', 'conflict'),
                               ('I need a wheelchair ride with my service dog on Monday.', 'ambiguous')]:
            with self.subTest(text=text):
                rec = self.simulate('healthcare-clinic-visit', spoken_request=text)
                self.assertEqual(rec['status'], 'needs_input')
                failed = {k for k, v in rec['verification'].items() if not v['passed']}
                self.assertEqual(failed, {'spoken_schedule_check'})
                self.assertEqual(rec['verification']['spoken_schedule_check']['status'], expected)
                self.assertTrue(rec['run_integrity']['passed'])

    def test_card_case_compares_speech_with_the_card(self):
        rec = self.simulate('healthcare-appointment-card', spoken_request=DEMO)
        self.assertEqual(rec['status'], 'awaiting_signoff')
        check = rec['verification']['spoken_schedule_check']
        self.assertEqual(check['status'], 'matches'); self.assertEqual(check['compared_with']['card']['arrive_by'], '09:45')
        late = self.simulate('healthcare-appointment-card', spoken_request=DEMO.replace('nine forty-five', 'nine thirty'))
        self.assertEqual(late['status'], 'needs_input')
        self.assertIn("card's arrive-by time 09:45", late['verification']['spoken_schedule_check']['reason'])

    def test_no_spoken_request_adds_no_check(self):
        self.assertNotIn('spoken_schedule_check', self.simulate('healthcare-clinic-visit')['verification'])
