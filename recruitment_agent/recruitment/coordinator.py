import json
import os
import time
from typing import TYPE_CHECKING, Any, Dict, List

from .agents import (
    Agent,
    DocumentAgent,
    EmailCommunicationAgent,
    JobAnalysisAgent,
    MatchingAgent,
    ResumeAnalysisAgent,
)

if TYPE_CHECKING:
    from mistralai.client import Mistral


class CoordinatorAgent(Agent):
    def __init__(self, client: "Mistral"):
        super().__init__("CoordinatorAgent", client)
        self.document_agent = DocumentAgent(client)
        self.job_analysis_agent = JobAnalysisAgent(client)
        self.resume_analysis_agent = ResumeAnalysisAgent(client)
        self.matching_agent = MatchingAgent(client)
        self.email_communication_agent = None

    def set_communication_agent(self, sender_email: str, app_password: str):
        """Initialize communication agent with email credentials"""
        self.email_communication_agent = EmailCommunicationAgent(self.client, sender_email, app_password)

    set_email_communication_agent = set_communication_agent

    def process_hiring_workflow(
        self,
        jd_file_path: str,
        resume_dir: str,
        output_path: str,
        threshold_score: float,
        calendly_link: str,
        email_subject: str,
        delay: float = 10,
        max_resumes: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Coordinate the entire hiring workflow from document processing to interview scheduling
        """
        results = []

        print("🤖 DocumentAgent extracting text from job description...")
        jd_text = self.document_agent.process((jd_file_path, os.path.basename(jd_file_path)))

        if not jd_text:
            print("❌ Failed to extract text from job description. Aborting.")
            return results

        print("🤖 JobAnalysisAgent analyzing job description...")
        job_requirements = self.job_analysis_agent.process(jd_text)

        time.sleep(delay)

        resume_files = [f for f in os.listdir(resume_dir) if os.path.isfile(os.path.join(resume_dir, f))]

        for filename in resume_files[:max_resumes]:
            file_path = os.path.join(resume_dir, filename)
            print(f"\n🤖 DocumentAgent processing resume: {filename}")

            resume_text = self.document_agent.process((file_path, filename))

            time.sleep(delay)

            if resume_text:
                print("🤖 ResumeAnalysisAgent extracting candidate profile...")
                candidate_profile = self.resume_analysis_agent.process(resume_text)

                print(f"🤖 MatchingAgent evaluating candidate {candidate_profile['contact_details']['name']}...")
                score = self.matching_agent.process((job_requirements, candidate_profile, resume_text))

                result = {
                    "file_name": filename,
                    "contact_details": candidate_profile["contact_details"],
                    "candidate_profile": candidate_profile,
                    "score": score,
                }

                results.append(result)

                time.sleep(delay)
            else:
                print(f"❌ DocumentAgent failed to extract text from {filename}. Skipping this resume.")

        results.sort(key=lambda x: x["score"]["total_score"], reverse=True)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n🤖 CoordinatorAgent saved results to {output_path}")

        print("\n===== CANDIDATE RANKING =====")
        for i, result in enumerate(results, 1):
            name = result["contact_details"]["name"]
            score = result["score"]["total_score"]
            print(f"{i}. {name}: {score}/100")

        if self.email_communication_agent:
            selected_candidates = [r for r in results if r["score"]["total_score"] >= threshold_score]

            print(f"\n🤖 EmailCommunicationAgent preparing to send interview invitations to {len(selected_candidates)} candidates who scored {threshold_score}+ out of 100...\n")

            for candidate in selected_candidates:
                response = self.email_communication_agent.process((candidate, calendly_link, email_subject))
                print(response)
                time.sleep(1)

        return results
