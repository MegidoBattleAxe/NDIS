import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING, Any, Dict

from .models import CandidateProfile, CandidateScore, JobRequirements

if TYPE_CHECKING:
    from mistralai.client import Mistral


def parse_structured(response, model_cls) -> Dict[str, Any]:
    """Extract a structured response as a plain dict.

    Prefers the SDK's parsed object when available and falls back to
    parsing the raw JSON content.
    """
    message = response.choices[0].message
    parsed = getattr(message, "parsed", None)
    if parsed is not None:
        if not isinstance(parsed, model_cls):
            parsed = model_cls.model_validate(parsed)
        return parsed.model_dump(mode="json")
    return model_cls.model_validate(json.loads(message.content)).model_dump(mode="json")


class Agent:
    def __init__(self, name: str, client: "Mistral"):
        self.name = name
        self.client = client

    def process(self, message):
        """Base process method - to be implemented by child classes"""
        raise NotImplementedError("Subclasses must implement process method")

    def communicate(self, recipient_agent, message):
        """Send message to another agent"""
        return recipient_agent.process(message)


class DocumentAgent(Agent):
    def __init__(self, client: "Mistral"):
        super().__init__("DocumentAgent", client)

    def process(self, file_info):
        """Process document extraction request"""
        file_path, file_name = file_info
        return self.extract_text_from_file(file_path, file_name)

    def extract_text_from_file(self, file_path: str, file_name: str) -> str:
        """Extract text from a file using Mistral OCR"""
        try:
            with open(file_path, "rb") as f:
                uploaded_file = self.client.files.upload(
                    file={
                        "file_name": file_name,
                        "content": f,
                    },
                    purpose="ocr",
                )

            signed_url = self.client.files.get_signed_url(file_id=uploaded_file.id)

            ocr_response = self.client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": signed_url.url,
                },
            )

            extracted_text = ""
            for page in ocr_response.pages:
                extracted_text += page.markdown + "\n\n"

            return extracted_text

        except Exception as e:
            print(f"Error extracting text from {file_name}: {str(e)}")
            return ""


class JobAnalysisAgent(Agent):
    def __init__(self, client: "Mistral"):
        super().__init__("JobAnalysisAgent", client)

    def process(self, jd_text):
        """Process job description text"""
        return self.extract_job_requirements(jd_text)

    def extract_job_requirements(self, jd_text: str) -> Dict[str, Any]:
        """Extract structured job requirements from a job description"""
        prompt = f"""
        Extract the key job requirements from the following job description.
        Focus on required skills, preferred skills, experience requirements, and education requirements.

        Job Description:
        {jd_text}
        """

        response = self.client.chat.parse(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": "Extract structured job requirements from the job description."},
                {"role": "user", "content": prompt},
            ],
            response_format=JobRequirements,
            temperature=0,
        )

        return parse_structured(response, JobRequirements)


class ResumeAnalysisAgent(Agent):
    def __init__(self, client: "Mistral"):
        super().__init__("ResumeAnalysisAgent", client)

    def process(self, resume_text):
        """Process resume text"""
        return self.extract_candidate_profile(resume_text)

    def extract_candidate_profile(self, resume_text: str) -> Dict[str, Any]:
        """Extract structured candidate information from resume text"""
        prompt = f"""
        Extract the candidate's contact details, skills, education, and experience from the following resume.
        Be thorough and include all relevant information.

        Resume:
        {resume_text}
        """

        response = self.client.chat.parse(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": "Extract structured candidate information from the resume."},
                {"role": "user", "content": prompt},
            ],
            response_format=CandidateProfile,
            temperature=0,
        )

        return parse_structured(response, CandidateProfile)


class MatchingAgent(Agent):
    def __init__(self, client: "Mistral"):
        super().__init__("MatchingAgent", client)

    def process(self, data):
        """Process job requirements and candidate profile to generate score"""
        job_requirements, candidate_profile, resume_text = data
        return self.evaluate_candidate(job_requirements, candidate_profile, resume_text)

    def evaluate_candidate(self, job_requirements, candidate_profile, resume_text: str) -> Dict[str, Any]:
        """Evaluate how well a candidate matches the job requirements"""
        job_req_json = json.dumps(job_requirements, indent=2)
        candidate_json = json.dumps(candidate_profile, indent=2)

        prompt = f"""
        Evaluate how well the candidate matches the job requirements.

        Job Requirements:
        {job_req_json}

        Candidate Profile:
        {candidate_json}

        Provide a detailed scoring breakdown, highlighting strengths and gaps.
        Assess the quality and relevance of the candidate's experience, not just keyword matches.
        Include confidence levels for your assessment.

        Technical skills should be scored out of 40 points.
        Experience should be scored out of 30 points.
        Education should be scored out of 15 points.
        Additional qualifications should be scored out of 15 points.
        The total score should be out of 100 points.
        """

        response = self.client.chat.parse(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": "Evaluate the candidate's match to the job requirements with detailed scoring."},
                {"role": "user", "content": prompt},
            ],
            response_format=CandidateScore,
            temperature=0.2,
        )

        return parse_structured(response, CandidateScore)


class EmailCommunicationAgent(Agent):
    def __init__(self, client: "Mistral", sender_email: str, app_password: str):
        super().__init__("EmailCommunicationAgent", client)
        self.sender_email = sender_email
        self.app_password = app_password

    def process(self, data):
        """Process email sending request"""
        candidate, calendly_link, subject = data
        return self.send_interview_invitation(candidate, calendly_link, subject)

    def send_interview_invitation(self, candidate, calendly_link: str, subject: str):
        """Generate and send personalized email to candidate"""
        name = candidate["contact_details"]["name"]
        email = candidate["contact_details"]["email"]

        html_content = f"""\
        <html>
          <body>
            <p>Hello {name},</p>
            <p>I'm the Hiring Manager from HireFive. Thank you for applying for the Data Scientist position at our company.</p>
            <p>We were impressed with your background and would like to schedule an initial screening call to discuss your experience and interest in the role.</p>
            <p>Please select a suitable time slot using our <a href="{calendly_link}">Calendly link</a>.</p>
            <p>Looking forward to speaking with you soon.</p>
            <p>Best regards,<br>
            Hiring Manager<br>
            HireFive</p>
          </body>
        </html>
        """

        if self.app_password:
            try:
                self.send_email(email, subject, html_content)
                return f"Email sent to {name} at {email}"
            except Exception as e:
                return f"Failed to send email to {name} ({email}): {str(e)}"
        else:
            return f"Would send email to {name} at {email} - Email subject: {subject}"

    def send_email(self, receiver_email, subject, html_content):
        """Send an email using Gmail SMTP"""
        message = MIMEMultipart("alternative")
        message["From"] = self.sender_email
        message["To"] = receiver_email
        message["Subject"] = subject

        message.attach(MIMEText(html_content, "html"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        try:
            server.starttls()
            server.login(self.sender_email, self.app_password)
            server.sendmail(self.sender_email, receiver_email, message.as_string())
        finally:
            server.quit()
