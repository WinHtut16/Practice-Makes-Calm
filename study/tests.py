"""Run with:  LLM_MOCK=1 python manage.py test study"""
import json
from collections import Counter

from django.conf import settings
from django.test import TestCase

from . import flow
from .content import stai_score
from .controller import next_level
from .counterbalance import sequence, shuffled_assignment
from .models import Message, Participant, Response, Round, Tag


class ControllerTests(TestCase):
    def test_rule(self):
        self.assertEqual(next_level(1, 3, 7), (2, "raise"))
        self.assertEqual(next_level(3, 3, 7), (3, "raise"))      # capped at 3
        self.assertEqual(next_level(2, 9, 7), (1, "lower"))      # stress wins over a good score
        self.assertEqual(next_level(2, 5, 2), (1, "lower"))
        self.assertEqual(next_level(1, 9, 1), (1, "lower"))      # floored at 1
        self.assertEqual(next_level(2, 7, 7), (2, "keep"))       # stress 7: neither branch
        self.assertEqual(next_level(2, 5, 5), (3, "raise"))       # raise threshold is DESC >= 5 since pilot P4
        self.assertEqual(next_level(2, 5, 4), (2, "keep"))


class CounterbalanceTests(TestCase):
    def test_balance(self):
        seqs = [sequence(n) for n in range(1, 19)]
        pair = Counter((d, s) for seq in seqs for d, s in seq)
        self.assertEqual(set(pair.values()), {6})                 # each design meets each scenario 6 times
        pos_d = Counter((i, d) for seq in seqs for i, (d, _) in enumerate(seq))
        pos_s = Counter((i, s) for seq in seqs for i, (_, s) in enumerate(seq))
        self.assertEqual(set(pos_d.values()), {6})
        self.assertEqual(set(pos_s.values()), {6})
        self.assertEqual(len({tuple(s) for s in seqs}), 18)       # 18 unique sequences

    def test_assignment_is_a_permutation(self):
        self.assertEqual(sorted(shuffled_assignment(5)), list(range(1, 19)))

    def test_paper_table(self):
        self.assertEqual(sequence(1), [("C", "S1"), ("F", "S2"), ("A", "S3")])
        self.assertEqual(sequence(5), [("F", "S2"), ("A", "S3"), ("C", "S1")])


class ScoringTests(TestCase):
    def test_stai(self):
        self.assertEqual(stai_score([4, 1, 1, 4, 4, 1]), 20.0)    # calmest
        self.assertEqual(stai_score([1, 4, 4, 1, 1, 4]), 80.0)    # most anxious


def likert(prefix, n, v):
    return {f"{prefix}{i}": str(v) for i in range(1, n + 1)}


class FullSessionTest(TestCase):
    """Click through an entire session in mock mode."""

    def setUp(self):
        self.assertTrue(settings.STUDY["MOCK"], "run tests with LLM_MOCK=1")

    def post_step(self, p, data=None):
        r = self.client.post(f"/s/{p.pid}/", {**(data or {}), "step_no": str(p.step)})
        self.assertEqual(r.status_code, 302, r.content[:400])
        p.refresh_from_db()

    def chat(self, p, text):
        r = self.client.post(f"/s/{p.pid}/api/chat/", json.dumps({"text": text}), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        return r.json()

    def test_session(self):
        p = flow.create_participant()
        self.assertTrue(p.pid.startswith("P"))
        # every page renders
        self.assertEqual(self.client.get(f"/s/{p.pid}/").status_code, 200)
        self.post_step(p, {"agree": "yes"})
        pre = {"age": "25", "gender": "woman", "program": "masters", "year": "1", "first_language": "Burmese",
               "english_comfort": "4", "prior_experience": "3", "llm_use": "daily",
               **likert("stai", 6, 2), **likert("se", 4, 4)}
        r = self.client.post(f"/s/{p.pid}/", {"age": "25", "step_no": str(p.step)})       # incomplete form re-renders with error
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Please answer")
        self.post_step(p, pre)
        # warm-up
        self.assertEqual(self.client.get(f"/s/{p.pid}/").status_code, 200)
        self.chat(p, "Hi Sam, can we swap?")
        res = self.chat(p, "I need Thursday for a training run.")
        self.assertTrue(res["done"])
        self.post_step(p)

        for b in range(3):
            block = p.blocks.get(position=b)
            self.post_step(p)  # card
            for r in range(settings.STUDY["PRACTICE_ROUNDS"]):
                self.assertEqual(self.client.get(f"/s/{p.pid}/").status_code, 200)
                done, n = False, 0
                while not done and n < 6:
                    n += 1
                    done = self.chat(p, "The sensor data was corrupted on Monday, so I need one more week. "
                                        "Could I submit next Friday? I will send partial results Wednesday.")["done"]
                self.post_step(p)  # leave round
                self.post_step(p, {"stress": "3"})
            rounds = Round.objects.filter(block=block, kind="practice").order_by("index")
            levels = [x.level for x in rounds]
            if block.design == "C":
                self.assertEqual(levels, [1] * settings.STUDY["PRACTICE_ROUNDS"])
            elif block.design == "F":
                self.assertEqual(levels, [3] * settings.STUDY["PRACTICE_ROUNDS"])
            else:
                self.assertEqual(levels[0], settings.STUDY["ADAPTIVE_START_LEVEL"])
                self.assertTrue(rounds[0].decision)
                self.assertIsNotNone(rounds[0].judge_total)
            # probe: opening + 3 replies
            self.assertEqual(self.client.get(f"/s/{p.pid}/").status_code, 200)
            self.chat(p, "Dr. Lee, I would like to ask for one more week.")
            for k in range(3):
                res = self.chat(p, f"Reply {k + 1}: because the data was corrupted, I will rerun it.")
            self.assertTrue(res["done"])
            probe = Round.objects.get(block=block, kind="probe")
            self.assertEqual(sorted(m.probe_line for m in probe.messages.filter(role="learner") if m.probe_line), [1, 2, 3])
            self.post_step(p)
            self.post_step(p, {**likert("stai", 6, 2), **likert("se", 4, 5), "difficulty": "4", "realism": "5"})
            self.assertEqual(self.client.get(f"/s/{p.pid}/").status_code, 200)  # tags page
            m = Message.objects.filter(round__block=block, round__index=1, role="drlee").first()
            self.post_step(p, {f"tag_{m.id}_helpful": "1", f"reason_{m.id}": "fair question"})
            if b < 2:
                self.post_step(p)  # break

        self.post_step(p)  # human role-play
        self.post_step(p, {**likert("stai", 6, 3), "human_vs_ai": "6"})
        r = self.client.post(f"/s/{p.pid}/", {"rank1": "Blue", "rank2": "Blue", "rank3": "Green", "step_no": str(p.step)})
        self.assertContains(r, "different rank")
        self.post_step(p, {"rank1": "Green", "rank2": "Blue", "rank3": "Orange"})
        self.assertEqual(flow.current_step(p)[0], "done")
        self.assertIsNotNone(p.finished)
        self.assertEqual(Response.objects.filter(participant=p, kind="block").count(), 3)
        self.assertEqual(Tag.objects.count(), 3)
        self.assertIn("stai_score", Response.objects.get(participant=p, kind="pre").data)

    def test_high_stress_flags_researcher(self):
        p = flow.create_participant()
        p.step = flow.STEPS.index(("round", 0, 0)); p.save()
        self.chat(p, "hello")
        self.post_step(p)
        r = self.client.post(f"/s/{p.pid}/", {"stress": "9", "step_no": str(p.step)})
        self.assertIn("pause=1", r["Location"])
        p.refresh_from_db()
        self.assertTrue(p.needs_attention)

    def test_pilot_ids_do_not_use_real_sequences(self):
        a = flow.create_participant(is_pilot=True)
        b = flow.create_participant()
        self.assertTrue(a.pid.startswith("PILOT"))
        self.assertEqual(Participant.objects.filter(is_pilot=False).count(), 1)
        self.assertNotEqual(a.sequence_no, b.sequence_no)


class DoubleSubmitTest(TestCase):
    """Regression: a double-click on 'Next practice round' skipped the next round (DoesNotExist)."""

    def test_double_click_does_not_skip_round(self):
        p = flow.create_participant(is_pilot=True)
        p.step = flow.STEPS.index(("stress", 2, 0)); p.save()
        flow.get_or_create_round(p, "practice", 2, 0)
        stale = str(p.step)
        self.client.post(f"/s/{p.pid}/", {"stress": "3", "step_no": stale})
        self.client.post(f"/s/{p.pid}/", {"stress": "3", "step_no": stale})  # second click, same page
        p.refresh_from_db()
        self.assertEqual(flow.current_step(p), ("round", 2, 1))
        self.assertTrue(p.events.filter(kind="stale_submit").exists())

    def test_broken_session_repairs_itself(self):
        """A participant already stuck on a stress page without its round (like PILOT18) is sent back to the round."""
        p = flow.create_participant(is_pilot=True)
        p.step = flow.STEPS.index(("stress", 2, 1)); p.save()
        r = self.client.get(f"/s/{p.pid}/")
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(flow.current_step(p), ("round", 2, 1))
        self.assertEqual(self.client.get(f"/s/{p.pid}/").status_code, 200)


class FiveParticipantTests(TestCase):
    def test_main_study_uses_the_five_balanced_sequences(self):
        ps = [flow.create_participant() for _ in range(5)]
        self.assertEqual(sorted(p.sequence_no for p in ps), [1, 6, 8, 10, 15])
        self.assertEqual(sorted(p.sequence_no for p in ps[:3]), [1, 6, 8])      # balanced square comes first
        with self.assertRaises(ValueError):
            flow.create_participant()
        square = [sequence(n) for n in (1, 6, 8)]
        self.assertEqual(len({(d, s) for seq in square for d, s in seq}), 9)     # each design meets each scenario once
        self.assertEqual(len({(i, d) for seq in square for i, (d, _) in enumerate(seq)}), 9)
        self.assertEqual(len({(i, s) for seq in square for i, (_, s) in enumerate(seq)}), 9)

    def test_pilot_never_uses_main_sequences(self):
        ps = [flow.create_participant(is_pilot=True) for _ in range(13)]
        self.assertFalse({p.sequence_no - 100 for p in ps} & {1, 6, 8, 10, 15})

    def test_adaptive_starts_at_l2(self):
        self.assertEqual(settings.STUDY["ADAPTIVE_START_LEVEL"], 2)


class TwoLaptopTests(TestCase):
    """Two laptops must never hand out the same ID, and their bundles must merge into one database."""

    def station(self, name, seqs):
        S = settings.STUDY
        self._old = (S["STATION"], S["STATION_SEQUENCES"])
        S["STATION"], S["STATION_SEQUENCES"] = name, seqs

    def tearDown(self):
        if hasattr(self, "_old"):
            settings.STUDY["STATION"], settings.STUDY["STATION_SEQUENCES"] = self._old

    def test_stations_partition_sequences_and_pilots(self):
        self.station("A", [1, 8, 15])
        a_main = [flow.create_participant().sequence_no for _ in range(3)]
        a_pilot = [flow.create_participant(is_pilot=True) for _ in range(2)]
        with self.assertRaises(ValueError):
            flow.create_participant()
        self.assertEqual(sorted(a_main), [1, 8, 15])
        self.assertTrue(all(p.pid.startswith("PILOTA") for p in a_pilot))
        a_pilot_seqs = set(flow.assignment_order(True))
        self.station("B", [6, 10])
        b_pilot_seqs = set(flow.assignment_order(True))
        self.assertFalse(a_pilot_seqs & b_pilot_seqs)
        self.assertEqual(sorted(flow.assignment_order(False)), [6, 10])

    def test_manual_sequence_choice(self):
        p = flow.create_participant(sequence_no=10)
        self.assertEqual(p.pid, "P10")
        with self.assertRaises(ValueError):
            flow.create_participant(sequence_no=10)

    def test_bundle_round_trip(self):
        from . import bundle
        from .version import config_hash
        p = flow.create_participant()
        self.assertEqual(p.config_hash, config_hash())
        p.step = flow.STEPS.index(("round", 0, 0)); p.save()
        self.client.post(f"/s/{p.pid}/api/chat/", json.dumps({"text": "hello"}), content_type="application/json")
        m = Message.objects.filter(role="drlee").first()
        Tag.objects.create(message=m, tag="helpful", reason="ok")
        data = json.loads(json.dumps(bundle.dump([p], "A", config_hash(), {}), default=str))
        n_msg, created = Message.objects.count(), p.created
        p.delete()
        q = bundle.load_participant(data["participants"][0])
        self.assertEqual(q.pid, p.pid)
        self.assertEqual(Message.objects.count(), n_msg)
        self.assertEqual(Tag.objects.get().message.round.block.position, 0)
        self.assertEqual(Participant.objects.get().created, created)
        self.assertEqual(q.blocks.count(), 3)


class HciFixTests(TestCase):
    def test_skip_round_and_researcher_skip(self):
        p = flow.create_participant(is_pilot=True)
        p.step = flow.STEPS.index(("round", 0, 0)); p.save()
        self.client.get(f"/s/{p.pid}/")
        r = self.client.post(f"/s/{p.pid}/api/timeout/", json.dumps({"reason": "skipped"}), content_type="application/json")
        self.assertEqual(r.json()["reason"], "skipped")
        self.assertEqual(Round.objects.get(kind="practice").end_reason, "skipped")
        p.refresh_from_db()
        before = p.step
        flow.researcher_skip(p)
        p.refresh_from_db()
        self.assertEqual(p.step, before + 1)
        self.assertTrue(p.events.filter(kind="researcher_skip").exists())

    def test_reflection_saved_and_tag_page_shows_own_turns(self):
        p = flow.create_participant(is_pilot=True)
        p.step = flow.STEPS.index(("round", 0, 0)); p.save()
        self.client.post(f"/s/{p.pid}/api/chat/", json.dumps({"text": "MY OWN TURN"}), content_type="application/json")
        self.client.post(f"/s/{p.pid}/", {"step_no": str(p.step)})
        p.refresh_from_db()
        self.client.post(f"/s/{p.pid}/", {"stress": "4", "reflection": "give a date", "step_no": str(p.step)})
        self.assertEqual(Round.objects.get(kind="practice", index=0).reflection, "give a date")
        p.step = flow.STEPS.index(("tags", 0, None)); p.save()
        r = self.client.get(f"/s/{p.pid}/")
        self.assertContains(r, "MY OWN TURN")

    def test_level_prompts_have_no_probe_wording(self):
        from .content import SCENARIOS
        from .prompts import dr_lee_system
        for sid, s in SCENARIOS.items():
            for lv in (1, 2, 3):
                text = dr_lee_system(sid, lv).lower()
                for line in s["probe"]:
                    self.assertNotIn(line.lower()[:25], text, f"{sid} L{lv} repeats probe wording")
