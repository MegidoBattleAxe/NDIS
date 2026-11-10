from typing import List, Optional

from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str = Field(description="Name of the skill or technology")
    level: Optional[str] = Field(default=None, description="Proficiency level (beginner, intermediate, advanced)")
    years: Optional[float] = Field(default=None, description="Years of experience with this skill")


class Education(BaseModel):
    degree: str = Field(description="Type of degree or certification obtained")
    field: str = Field(description="Field of study or specialization")
    institution: str = Field(description="Name of educational institution")
    year_completed: Optional[int] = Field(default=None, description="Year when degree was completed")
    gpa: Optional[float] = Field(default=None, description="Grade Point Average, typically on 4.0 scale")


class Experience(BaseModel):
    title: str = Field(description="Job title or position held")
    company: str = Field(description="Name of employer or organization")
    duration_years: float = Field(description="Duration of employment in years")
    skills_used: List[str] = Field(description="Skills utilized in this role")
    achievements: List[str] = Field(description="Key accomplishments or responsibilities")
    relevance_score: Optional[float] = Field(default=None, description="Relevance to current job opening (0-10 scale)")


class ContactDetails(BaseModel):
    name: str = Field(description="Full name of the candidate")
    email: str = Field(description="Primary email address for contact")
    phone: Optional[str] = Field(default=None, description="Phone number with country code if applicable")
    location: Optional[str] = Field(default=None, description="Current city and country/state")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    website: Optional[str] = Field(default=None, description="Personal or portfolio website URL")


class JobRequirements(BaseModel):
    required_skills: List[Skill] = Field(description="Skills that are mandatory for the position")
    preferred_skills: List[Skill] = Field(description="Skills that are desired but not required")
    min_experience_years: float = Field(description="Minimum years of experience required")
    required_education: List[Education] = Field(description="Mandatory educational qualifications")
    preferred_domains: List[str] = Field(description="Industry domains or sectors preferred for experience")


class CandidateProfile(BaseModel):
    contact_details: ContactDetails = Field(description="Candidate's personal and contact information")
    skills: List[Skill] = Field(description="Technical and soft skills possessed by the candidate")
    education: List[Education] = Field(description="Educational background and qualifications")
    experience: List[Experience] = Field(description="Professional work history and experience")


class SkillMatch(BaseModel):
    skill_name: str = Field(description="Name of the skill being evaluated")
    present: bool = Field(description="Whether the candidate possesses this skill")
    match_level: float = Field(description="How well the candidate's skill matches the requirement (0-10 scale)")
    confidence: float = Field(description="Confidence in the skill evaluation (0-1 scale)")
    notes: str = Field(description="Additional context about the skill match assessment")


class CandidateScore(BaseModel):
    technical_skills_score: float = Field(description="Assessment of technical capabilities (0-40 points)")
    experience_score: float = Field(description="Evaluation of relevant work experience (0-30 points)")
    education_score: float = Field(description="Rating of educational qualifications (0-15 points)")
    additional_score: float = Field(description="Score for other relevant factors (0-15 points)")
    total_score: float = Field(description="Aggregate candidate evaluation score (0-100)")
    key_strengths: List[str] = Field(description="Primary candidate advantages for this role")
    key_gaps: List[str] = Field(description="Areas where the candidate lacks desired qualifications")
    confidence: float = Field(description="Overall confidence in the evaluation accuracy (0-1 scale)")
    notes: str = Field(description="Supplementary observations about the candidate fit")


class CandidateResult(BaseModel):
    file_name: str = Field(description="Name of the source resume file")
    contact_details: ContactDetails = Field(description="Candidate's contact information")
    candidate_profile: CandidateProfile = Field(description="Complete extracted candidate profile")
    score: CandidateScore = Field(description="Detailed evaluation scores and assessment")
