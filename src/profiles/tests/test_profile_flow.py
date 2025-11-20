# src/profiles/tests/test_profile_flow.py
"""
Test suite: Profile exam submission and validation flow

Covers the full end-to-end behaviour of the student profile exam form, ensuring:

1. Exam type–specific rules:
   • IELTS / TOEFL (0–120) clear any Cambridge-only fields (grade, use_of_english).
   • Cambridge C1/C2 correctly save all sub-scores and additional fields.
   • Overall score auto-computes according to exam type (sum, avg, or half-step).

2. Honour code enforcement:
   • No data is persisted unless academic_integrity_confirmed is ticked.

3. Exam toggling logic:
   • Switching "Has recent English exam" to False wipes all related exam fields.

All tests use Django’s built-in TestCase and a temporary in-memory database.
They assert both correct persistence and field-clearing behaviour to guarantee
consistency between frontend form logic and backend validation.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from profiles.models import Profile

User = get_user_model()


class ProfileExamFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="student@example.com",
            password="pw12345678",
            role="student",
            first_name="Stu",
            last_name="Dent",
        )
        assert self.client.login(email="student@example.com", password="pw12345678")
        # The view uses get_or_create; this ensures we have an instance to compare against.
        self.profile = Profile.objects.get_or_create(user=self.user)[0]
        self.url = reverse("profiles:profile")

        # A helper to build a valid “base” payload for the form
        today = date.today()
        self.base = {
            # base fields
            "phone": "+44 1234 567890",
            "subject_area": "computing",
            "requires_uk_student_visa": "True",
            # honour code must be ticked to allow save
            "academic_integrity_confirmed": "true",
            # exam switch + split date
            "has_recent_english_exam": "True",
            "exam_type": "",
            "exam_day": str(today.day),
            "exam_month": str(today.month),
            "exam_year": str(today.year),
            # scores (will adjust per test)
            "reading_score": "",
            "listening_score": "",
            "writing_score": "",
            "speaking_score": "",
            "overall_score": "",
            "overall_manual_override": "",
            # cambridge extras
            "cambridge_grade": "",
            "cambridge_use_of_english": "",
        }

    def post(self, data):
        """POST helper that returns the reloaded Profile."""
        resp = self.client.post(self.url, data, follow=True)
        # Always re-load from DB
        prof = Profile.objects.get(user=self.user)
        return resp, prof

    def test_ielts_submission_clears_cambridge_fields(self):
        data = self.base | {
            "exam_type": "ielts",
            "reading_score": "6.5",
            "listening_score": "6.0",
            "writing_score": "6.5",
            "speaking_score": "6.0",
            # try to sneak in Cambridge-only fields (should be cleared on save)
            "cambridge_grade": "a",
            "cambridge_use_of_english": "195",
        }
        resp, prof = self.post(data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(prof.academic_integrity_confirmed)

        self.assertEqual(prof.exam_type, "ielts")
        # overall should auto-calc (nearest 0.5) = avg(6.5,6.0,6.5,6.0)=6.25→6.5
        self.assertEqual(float(prof.overall_score), 6.5)

        # Cambridge-only fields must be cleared for non-C1/C2
        self.assertIsNone(prof.cambridge_grade)
        self.assertIsNone(prof.cambridge_use_of_english)

    def test_toefl_submission_clears_cambridge_fields(self):
        data = self.base | {
            "exam_type": "toefl_120",
            "reading_score": "25",
            "listening_score": "23",
            "writing_score": "24",
            "speaking_score": "22",
            "cambridge_grade": "b",  # should be ignored/cleared
            "cambridge_use_of_english": "200",  # should be ignored/cleared
        }
        resp, prof = self.post(data)
        self.assertEqual(resp.status_code, 200)

        # exam_type should be stored using the new key
        self.assertEqual(prof.exam_type, "toefl_120")
        # overall should be sum of subs for TOEFL (0–120)
        self.assertEqual(float(prof.overall_score), 25 + 23 + 24 + 22)

        # Cambridge-only fields must be cleared for non-C1/C2
        self.assertIsNone(prof.cambridge_grade)
        self.assertIsNone(prof.cambridge_use_of_english)

    def test_cambridge_c1_submission_saves_all_scores_and_cambridge_fields(self):
        data = self.base | {
            "exam_type": "c1",
            "reading_score": "190",
            "listening_score": "185",
            "writing_score": "188",
            "speaking_score": "186",
            "cambridge_grade": "b",
            "cambridge_use_of_english": "189",
        }
        resp, prof = self.post(data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(prof.exam_type, "c1")
        # overall should be avg rounded to nearest int
        self.assertEqual(float(prof.overall_score), round((190 + 185 + 188 + 186) / 4))
        self.assertEqual(prof.cambridge_grade, "b")
        self.assertEqual(float(prof.cambridge_use_of_english), 189.0)

    def test_cambridge_c2_submission_saves_all_scores_and_cambridge_fields(self):
        data = self.base | {
            "exam_type": "c2",
            "reading_score": "210",
            "listening_score": "205",
            "writing_score": "209",
            "speaking_score": "206",
            "cambridge_grade": "a",
            "cambridge_use_of_english": "210",
        }
        resp, prof = self.post(data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(prof.exam_type, "c2")
        self.assertEqual(float(prof.overall_score), round((210 + 205 + 209 + 206) / 4))
        self.assertEqual(prof.cambridge_grade, "a")
        self.assertEqual(float(prof.cambridge_use_of_english), 210.0)

    def test_no_honour_code_blocks_save(self):
        # Start with a known value and ensure it doesn’t flip without consent
        prof_before = Profile.objects.get(user=self.user)
        self.assertFalse(prof_before.academic_integrity_confirmed)

        data = self.base | {
            "academic_integrity_confirmed": "",  # NOT ticked
            "exam_type": "ielts",
            "reading_score": "6.5",
            "listening_score": "6.0",
            "writing_score": "6.5",
            "speaking_score": "6.0",
        }
        resp = self.client.post(self.url, data)
        # Form should be invalid; page re-rendered with 200
        self.assertEqual(resp.status_code, 200)

        prof_after = Profile.objects.get(user=self.user)
        # Honour code should still be False
        self.assertFalse(prof_after.academic_integrity_confirmed)
        # Scores should not have been persisted as a “complete” profile without consent:
        # (Either remain None or computed only when valid; we assert remains None.)
        self.assertIsNone(prof_after.overall_score)

    def test_turning_off_exam_clears_all_exam_fields(self):
        data = self.base | {
            "has_recent_english_exam": "False",
            # When toggled off in the UI all exam-related inputs are cleared
            "exam_type": "",
            "exam_day": "",
            "exam_month": "",
            "exam_year": "",
            "reading_score": "",
            "listening_score": "",
            "writing_score": "",
            "speaking_score": "",
            "overall_score": "",
            "cambridge_grade": "",
            "cambridge_use_of_english": "",
        }
        resp, prof = self.post(data)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(prof.has_recent_english_exam)
        self.assertEqual(prof.exam_type, "")
        self.assertIsNone(prof.exam_date)

    def test_cannot_edit_after_profile_marked_complete(self):
        complete_payload = self.base | {
            "exam_type": "ielts",
            "reading_score": "7.0",
            "listening_score": "7.0",
            "writing_score": "7.0",
            "speaking_score": "7.0",
        }
        resp, prof = self.post(complete_payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(prof.is_complete())

        resp = self.client.post(
            self.url,
            complete_payload | {"phone": "+44 0000 000000"},
        )
        self.assertEqual(resp.status_code, 403)

        prof.refresh_from_db()
        self.assertEqual(prof.phone, "+44 1234 567890")
