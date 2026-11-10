import argparse
import os
import sys
from pathlib import Path


def load_dotenv(path: str = ".env") -> None:
    """Load KEY=VALUE pairs from a .env file without overriding existing env vars."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Multi-Agent Recruitment Workflow (Mistral AI)",
    )
    parser.add_argument("--jd", default="data/job_description.pdf", help="Path to the job description PDF")
    parser.add_argument("--resumes", default="data/resumes", help="Directory containing candidate resume PDFs")
    parser.add_argument("--output", default="candidate_results.json", help="Where to write the ranked results JSON")
    parser.add_argument("--threshold", type=float, default=65, help="Minimum total score (0-100) to receive an interview invitation")
    parser.add_argument("--max-resumes", type=int, default=5, help="Maximum number of resumes to process")
    parser.add_argument("--delay", type=float, default=10, help="Delay in seconds between API calls (rate-limit safety)")
    parser.add_argument("--calendly-link", default=os.environ.get("CALENDLY_LINK", ""), help="Calendly scheduling link sent to candidates")
    parser.add_argument("--email-subject", default=os.environ.get("EMAIL_SUBJECT", "HireFive: Next Steps for Your Data Scientist Application"))
    parser.add_argument("--no-email", action="store_true", help="Skip the EmailCommunicationAgent entirely")
    return parser.parse_args(argv)


def main(argv=None):
    load_dotenv()
    args = parse_args(argv)

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("Error: set MISTRAL_API_KEY in the environment or in a .env file (get one at https://console.mistral.ai/api-keys)", file=sys.stderr)
        return 1

    if not Path(args.jd).is_file():
        print(f"Error: job description not found: {args.jd}", file=sys.stderr)
        return 1
    if not Path(args.resumes).is_dir():
        print(f"Error: resume directory not found: {args.resumes}", file=sys.stderr)
        return 1

    from mistralai.client import Mistral

    from recruitment.coordinator import CoordinatorAgent

    client = Mistral(api_key=api_key)
    coordinator = CoordinatorAgent(client)

    if not args.no_email:
        sender_email = os.environ.get("SENDER_EMAIL", "")
        app_password = os.environ.get("APP_PASSWORD", "")
        coordinator.set_communication_agent(sender_email, app_password)
        if not app_password:
            print("Note: APP_PASSWORD not set - emails will be generated but not sent (dry-run).")

    results = coordinator.process_hiring_workflow(
        jd_file_path=args.jd,
        resume_dir=args.resumes,
        output_path=args.output,
        threshold_score=args.threshold,
        calendly_link=args.calendly_link,
        email_subject=args.email_subject,
        delay=args.delay,
        max_resumes=args.max_resumes,
    )

    return 0 if results is not None else 1


if __name__ == "__main__":
    sys.exit(main())
