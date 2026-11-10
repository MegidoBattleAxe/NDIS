import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recruitment.agents import EmailCommunicationAgent
from recruitment.coordinator import CoordinatorAgent
from recruitment.models import CandidateProfile, CandidateScore, ContactDetails, JobRequirements

FAKE_JD = {
    "required_skills": [{"name": "Python", "level": "advanced", "years": 3.0}],
    "preferred_skills": [{"name": "Deep Learning", "level": "intermediate", "years": None}],
    "min_experience_years": 3.0,
    "required_education": [],
    "preferred_domains": ["tech"],
}

FAKE_SCORES = [80.0, 55.0, 72.0]


def make_profile(name):
    return CandidateProfile(
        contact_details=ContactDetails(name=name, email=f"{name.split()[0].lower()}@example.com"),
        skills=[],
        education=[],
        experience=[],
    )


class FakeChat:
    def __init__(self):
        self.calls = 0

    def parse(self, model, messages, response_format, temperature):
        if response_format is JobRequirements:
            obj = JobRequirements.model_validate(FAKE_JD)
        elif response_format is CandidateProfile:
            self.calls += 1
            obj = make_profile(f"Candidate {self.calls}")
        elif response_format is CandidateScore:
            total = FAKE_SCORES[(self.calls - 1) % len(FAKE_SCORES)]
            obj = CandidateScore(
                technical_skills_score=total * 0.4,
                experience_score=total * 0.3,
                education_score=total * 0.15,
                additional_score=total * 0.15,
                total_score=total,
                key_strengths=["strong skills"],
                key_gaps=[],
                confidence=0.9,
                notes="fake",
            )
        else:
            raise AssertionError(f"unexpected response_format: {response_format}")
        message = SimpleNamespace(parsed=obj, content=obj.model_dump_json())
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeFiles:
    def upload(self, file, purpose):
        assert purpose == "ocr"
        return SimpleNamespace(id=file["file_name"])

    def get_signed_url(self, file_id):
        return SimpleNamespace(url=f"https://signed.example/{file_id}")


class FakeOCR:
    def __init__(self, fail_on=None):
        self.fail_on = fail_on or set()
        self.seen = []

    def process(self, model, document):
        assert model == "mistral-ocr-latest"
        url = document["document_url"]
        if any(name in url for name in self.fail_on):
            raise RuntimeError("OCR failed")
        self.seen.append(url)
        page = SimpleNamespace(markdown="# Fake resume\nSkills: Python")
        return SimpleNamespace(pages=[page])


class FakeClient:
    def __init__(self, ocr=None):
        self.files = FakeFiles()
        self.ocr = ocr or FakeOCR()
        self.chat = FakeChat()


class RecordingEmailAgent(EmailCommunicationAgent):
    def __init__(self, client):
        super().__init__(client, sender_email="hr@example.com", app_password="")
        self.sent = []

    def process(self, data):
        response = super().process(data)
        self.sent.append(response)
        return response


class WorkflowSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.jd_path = os.path.join(self.tmp.name, "job_description.pdf")
        self.resume_dir = os.path.join(self.tmp.name, "resumes")
        os.makedirs(self.resume_dir)
        with open(self.jd_path, "wb") as f:
            f.write(b"%PDF-fake-jd")
        for name in ["a.pdf", "b.pdf", "c.pdf"]:
            with open(os.path.join(self.resume_dir, name), "wb") as f:
                f.write(b"%PDF-fake-resume")
        self.output_path = os.path.join(self.tmp.name, "results.json")

    def run_workflow(self, client, threshold=65):
        coordinator = CoordinatorAgent(client)
        coordinator.email_communication_agent = RecordingEmailAgent(client)
        return coordinator.process_hiring_workflow(
            jd_file_path=self.jd_path,
            resume_dir=self.resume_dir,
            output_path=self.output_path,
            threshold_score=threshold,
            calendly_link="https://calendly.com/fake",
            email_subject="Fake subject",
            delay=0,
            max_resumes=5,
        )

    def test_end_to_end_ranking_and_email_threshold(self):
        client = FakeClient()
        results = self.run_workflow(client, threshold=65)

        self.assertEqual(len(results), 3)
        scores = [r["score"]["total_score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(scores, [80.0, 72.0, 55.0])

        for r in results:
            self.assertIn("file_name", r)
            self.assertIn("contact_details", r)
            self.assertIn("candidate_profile", r)
            self.assertIn("score", r)
            self.assertIn("name", r["contact_details"])

        with open(self.output_path) as f:
            saved = json.load(f)
        self.assertEqual(len(saved), 3)
        self.assertEqual(saved[0]["score"]["total_score"], 80.0)

    def test_emails_only_for_candidates_above_threshold(self):
        client = FakeClient()
        coordinator = CoordinatorAgent(client)
        coordinator.email_communication_agent = RecordingEmailAgent(client)
        results = coordinator.process_hiring_workflow(
            jd_file_path=self.jd_path,
            resume_dir=self.resume_dir,
            output_path=self.output_path,
            threshold_score=65,
            calendly_link="https://calendly.com/fake",
            email_subject="Fake subject",
            delay=0,
            max_resumes=5,
        )
        sent = coordinator.email_communication_agent.sent
        self.assertEqual(len(sent), 2)
        for msg in sent:
            self.assertIn("Would send email", msg)
        above = [r for r in results if r["score"]["total_score"] >= 65]
        self.assertEqual(len(above), 2)

    def test_failed_ocr_resume_is_skipped(self):
        client = FakeClient(ocr=FakeOCR(fail_on={"b.pdf"}))
        results = self.run_workflow(client, threshold=65)
        self.assertEqual(len(results), 2)
        self.assertNotIn("b.pdf", [r["file_name"] for r in results])

    def test_max_resumes_limits_processing(self):
        client = FakeClient()
        coordinator = CoordinatorAgent(client)
        results = coordinator.process_hiring_workflow(
            jd_file_path=self.jd_path,
            resume_dir=self.resume_dir,
            output_path=self.output_path,
            threshold_score=65,
            calendly_link="https://calendly.com/fake",
            email_subject="Fake subject",
            delay=0,
            max_resumes=2,
        )
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
