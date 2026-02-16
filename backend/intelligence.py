"""
Intelligence Engine for AutoCareer.
Scores jobs against resume and generates customized cover letters using RAG.
HARDENED VERSION: Robust error handling and graceful fallbacks.
"""

import os
import re
from typing import Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
from database import get_db
from profile_engine import ProfileEngine
import logging
import sys

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class IntelligenceEngine:
    """LLM-based job analysis and cover letter generation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            self.client = None
            logger.warning("No OpenAI API key provided. Using fallback scoring.")
        
        self.profile_engine = ProfileEngine()
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract technical keywords from text. HARDENED: handles None/empty."""
        if not text:
            return []
        
        # Common ML/tech keywords
        keywords = [
            'python', 'java', 'javascript', 'c++', 'machine learning', 'deep learning',
            'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'sql', 'nosql',
            'aws', 'gcp', 'azure', 'docker', 'kubernetes', 'git', 'nlp', 'computer vision',
            'data science', 'statistics', 'algorithms', 'distributed systems', 'api',
            'rest', 'graphql', 'react', 'node.js', 'typescript', 'mongodb', 'postgresql',
            'neural networks', 'transformers', 'llm', 'bert', 'gpt', 'reinforcement learning',
            'hadoop', 'spark', 'kafka', 'redis', 'elasticsearch', 'airflow', 'mlops'
        ]
        
        try:
            text_lower = text.lower()
            found_keywords = [kw for kw in keywords if kw in text_lower]
            return found_keywords
        except Exception as e:
            logger.error(f"Keyword extraction error: {e}")
            return []
    
    def calculate_keyword_overlap(self, resume_text: str, job_description: str) -> float:
        """Calculate keyword overlap between resume and job description. HARDENED."""
        try:
            resume_keywords = set(self.extract_keywords(resume_text or ""))
            job_keywords = set(self.extract_keywords(job_description or ""))
            
            if not job_keywords:
                return 50.0  # Neutral score when no keywords found
            
            if not resume_keywords:
                return 0.0
            
            overlap = len(resume_keywords.intersection(job_keywords))
            score = overlap / len(job_keywords)
            
            return min(score * 100, 100)  # Cap at 100
        except Exception as e:
            logger.error(f"Keyword overlap calculation error: {e}")
            return 50.0  # Neutral fallback
    
    def score_job_fallback(self, job: Dict, resume_text: str) -> Tuple[float, str]:
        """
        Fallback scoring without LLM API. HARDENED: Always returns valid results.
        Returns: (score, rationale)
        """
        try:
            # Safely extract job text
            title = job.get('title', '')
            description = job.get('description', '')
            requirements = job.get('requirements', '')
            
            job_text = f"{title} {description} {requirements}"
            
            # Keyword-based scoring
            keyword_score = self.calculate_keyword_overlap(resume_text or "", job_text)
            
            # Extract matching keywords
            resume_keywords = set(self.extract_keywords(resume_text or ""))
            job_keywords = set(self.extract_keywords(job_text))
            matching = resume_keywords.intersection(job_keywords)
            
            rationale = f"Keyword overlap score: {keyword_score:.1f}/100. "
            
            if matching:
                rationale += f"Matching skills: {', '.join(list(matching)[:10])}. "
            else:
                rationale += "No direct skill matches found. "
            
            if keyword_score > 70:
                rationale += "Strong technical alignment."
            elif keyword_score > 40:
                rationale += "Moderate technical alignment."
            else:
                rationale += "Limited technical alignment."
            
            return keyword_score, rationale
            
        except Exception as e:
            logger.error(f"Fallback scoring error: {e}")
            return 50.0, "Unable to analyze job details. Neutral score assigned."
    
    def score_job_with_llm(self, job: Dict, resume_text: str) -> Tuple[float, str]:
        """
        Score job using LLM for deeper analysis. HARDENED: Always returns valid results.
        Returns: (score, rationale)
        """
        if not self.client:
            return self.score_job_fallback(job, resume_text)
        
        try:
            job_text = f"""
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Description: {job.get('description', 'N/A')[:2000]}
Requirements: {job.get('requirements', 'N/A')[:1000]}
"""
            
            prompt = f"""You are an expert technical recruiter with deep knowledge of ML/AI and software engineering roles. Your task is to provide a precise, data-driven assessment of candidate-job fit.

CANDIDATE PROFILE:
{(resume_text or '')[:3000]}

JOB POSTING:
{job_text}

ANALYSIS FRAMEWORK:
Evaluate the following dimensions (0-100 each):
1. Technical Skills Match: Does the candidate have the required technical stack? (programming languages, frameworks, tools)
2. Experience Level Alignment: Does the candidate's years of experience match the seniority level? (junior: 0-2y, mid: 2-5y, senior: 5+y)
3. Domain Expertise: Does the candidate have relevant domain experience? (e.g., NLP, computer vision, MLOps, etc.)
4. Required vs Nice-to-Have: What percentage of "required" vs "nice-to-have" qualifications does the candidate meet?

SCORING RUBRIC:
- 90-100: Exceptional fit - Candidate exceeds most requirements
- 75-89: Strong fit - Candidate meets all core requirements plus some preferred
- 60-74: Good fit - Candidate meets most core requirements
- 40-59: Moderate fit - Candidate meets some requirements, gaps exist
- 0-39: Poor fit - Significant misalignment with requirements

INSTRUCTIONS:
1. Calculate an overall fit score (0-100) using the framework above
2. Provide a detailed rationale with:
   - Specific matching skills/technologies (list 3-5)
   - Key strengths that align with the role
   - Any notable gaps or missing qualifications
   - Experience level assessment

Format your response EXACTLY as:
SCORE: [number between 0-100]
RATIONALE: [Your detailed analysis - 3-4 sentences covering matches, strengths, and gaps]
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert technical recruiter specializing in ML/AI and software engineering roles. You provide precise, evidence-based candidate assessments with specific examples from their background."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500,
                timeout=30
            )
            
            content = response.choices[0].message.content
            
            # Parse response
            score_match = re.search(r'SCORE:\s*(\d+(?:\.\d+)?)', content)
            rationale_match = re.search(r'RATIONALE:\s*(.+)', content, re.DOTALL)
            
            if score_match and rationale_match:
                score = float(score_match.group(1))
                rationale = rationale_match.group(1).strip()
                logger.info(f"LLM scoring successful: {score}/100")
                return min(score, 100), rationale
            else:
                logger.warning("Could not parse LLM response, using fallback")
                return self.score_job_fallback(job, resume_text)
                
        except Exception as e:
            logger.error(f"LLM scoring error: {e}")
            return self.score_job_fallback(job, resume_text)
    
    def analyze_job(self, job_id: int, profile_id: int = 1) -> Dict:
        """
        Analyze a job and update database with score. HARDENED: Handles all edge cases.
        Returns: analysis results
        """
        try:
            db = get_db()
            
            # Get job and profile with validation
            job = db.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found in database")
            
            profile = db.get_profile(profile_id)
            if not profile:
                raise ValueError(f"Profile {profile_id} not found in database")
            
            # Score the job
            resume_text = profile.get('resume_text', '') or profile.get('skills', '') or ''
            score, rationale = self.score_job_with_llm(job, resume_text)
            
            # Update database
            db.update_job_analysis(job_id, score, rationale, status='analyzed')
            
            logger.info(f"Analyzed job {job_id}: {job.get('title', 'Unknown')} - Score: {score:.1f}")
            
            return {
                'job_id': job_id,
                'title': job.get('title', 'Unknown'),
                'company': job.get('company', 'Unknown'),
                'score': score,
                'rationale': rationale
            }
            
        except Exception as e:
            logger.error(f"Job analysis error for job_id {job_id}: {e}")
            # Return fallback result instead of crashing
            return {
                'job_id': job_id,
                'title': 'Unknown',
                'company': 'Unknown',
                'score': 50.0,
                'rationale': f"Analysis failed: {str(e)}. Neutral score assigned."
            }
    
    def scrape_company_website(self, company_url: str) -> str:
        """
        Scrape company website for context. HARDENED: Safe against failures.
        Returns: extracted text content
        """
        try:
            response = requests.get(company_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            
            # Limit length
            return text[:5000]
            
        except Exception as e:
            logger.error(f"Error scraping company website {company_url}: {e}")
            return ""
    
    def generate_cover_letter_fallback(self, job: Dict, profile: Dict) -> str:
        """Generate basic cover letter without LLM. HARDENED."""
        try:
            company = job.get('company', 'the company')
            title = job.get('title', 'the position')
            name = profile.get('name', 'Candidate')
            skills = profile.get('skills', 'technology')[:100]
            
            return f"""Dear Hiring Manager at {company},

I am excited to apply for the {title} position. With my background in {skills} and relevant experience in the field, I believe I would be a strong fit for your team.

My technical skills align well with the requirements outlined in your job posting. I am particularly drawn to {company}'s work and would welcome the opportunity to contribute to your team's success.

Thank you for considering my application. I look forward to discussing how my background and skills would benefit {company}.

Best regards,
{name}
"""
        except Exception as e:
            logger.error(f"Fallback cover letter generation error: {e}")
            return "Error generating cover letter. Please write manually."
    
    def generate_cover_letter(self, job_id: int, profile_id: int = 1, 
                            company_context: str = "") -> str:
        """
        Generate highly persuasive cover letter using advanced RAG. HARDENED.
        Returns: cover letter text
        """
        try:
            db = get_db()
            
            job = db.get_job(job_id)
            profile = db.get_profile(profile_id)
            
            if not job or not profile:
                raise ValueError("Job or profile not found")
            
            if not self.client:
                return self.generate_cover_letter_fallback(job, profile)
            
            # If company context not provided, try to scrape
            if not company_context and job.get('url'):
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(job['url'])
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    company_context = self.scrape_company_website(base_url)
                except:
                    pass
            
            prompt = f"""You are an expert career coach and professional writer specializing in crafting compelling, persuasive job application materials for technical roles. Your cover letters have helped candidates land positions at top tech companies.

CANDIDATE PROFILE:
Name: {profile.get('name', 'The candidate')}
Technical Skills: {(profile.get('skills', 'N/A'))[:800]}
Professional Experience: {(profile.get('experience', 'N/A'))[:1200]}
Education: {(profile.get('education', 'N/A'))[:500]}

TARGET ROLE:
Position: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Job Description: {(job.get('description', 'N/A'))[:1500]}
Key Requirements: {(job.get('requirements', 'N/A'))[:800]}

COMPANY INTELLIGENCE:
{company_context[:2000] if company_context else 'Research the company values and mission independently'}

WRITING GUIDELINES:
1. OPENING (Hook): Start with a compelling statement that shows genuine enthusiasm and immediately demonstrates understanding of the role
2. VALUE PROPOSITION (Body): 
   - Identify 2-3 key requirements from the job description
   - For each, provide a SPECIFIC achievement or experience that demonstrates mastery
   - Use quantifiable results when possible (e.g., "improved model accuracy by 15%", "reduced latency by 40%")
   - Show technical depth with specific technologies/methodologies
3. COMPANY ALIGNMENT (Why Them):
   - Reference specific company initiatives, products, or values
   - Connect your background to their mission
   - Show you've done your research
4. CLOSING (Call to Action): Express eagerness to discuss how you can contribute, professional yet confident

TONE: Professional, confident (not arrogant), specific (not generic), enthusiastic (not desperate)

LENGTH: 3-4 concise paragraphs (250-350 words total)

CRITICAL RULES:
- NO clichés like "I am writing to express my interest" or "I believe I would be a great fit"
- USE specific examples and achievements
- DEMONSTRATE technical expertise through concrete details
- PERSONALIZE to this specific role and company
- AVOID generic statements that could apply to any job

Write a high-impact cover letter that will make the hiring manager want to interview this candidate:
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an elite career advisor specializing in technical roles. Your cover letters are known for being specific, achievement-focused, and highly persuasive. You avoid generic language and always include concrete examples."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=700,
                timeout=60
            )
            
            cover_letter = response.choices[0].message.content.strip()
            
            # Store draft in database
            draft_id = db.insert_draft(
                job_id=job_id,
                profile_id=profile_id,
                cover_letter=cover_letter,
                company_context=company_context[:1000] if company_context else None
            )
            
            logger.info(f"Generated high-grade cover letter for job {job_id} (draft_id: {draft_id})")
            
            return cover_letter
            
        except Exception as e:
            logger.error(f"LLM cover letter generation error: {e}")
            # Always return fallback instead of crashing
            db = get_db()
            job = db.get_job(job_id)
            profile = db.get_profile(profile_id)
            return self.generate_cover_letter_fallback(job or {}, profile or {})
    
    def analyze_and_draft(self, job_id: int, profile_id: int = 1) -> Dict:
        """
        Complete analysis and draft generation pipeline. HARDENED.
        Returns: combined results
        """
        try:
            # Analyze job
            analysis = self.analyze_job(job_id, profile_id)
            
            # Generate cover letter for high-scoring jobs
            if analysis['score'] >= 50:
                try:
                    cover_letter = self.generate_cover_letter(job_id, profile_id)
                    analysis['cover_letter'] = cover_letter
                except Exception as e:
                    logger.error(f"Cover letter generation failed: {e}")
                    analysis['cover_letter'] = None
            else:
                analysis['cover_letter'] = None
                logger.info(f"Skipping cover letter for low-scoring job (score: {analysis['score']:.1f})")
            
            return analysis
            
        except Exception as e:
            logger.error(f"analyze_and_draft failed for job {job_id}: {e}")
            return {
                'job_id': job_id,
                'title': 'Unknown',
                'company': 'Unknown',
                'score': 50.0,
                'rationale': f"Pipeline error: {str(e)}",
                'cover_letter': None
            }


def main():
    """Test intelligence engine."""
    engine = IntelligenceEngine()
    
    # Test with a sample job (requires job in database)
    db = get_db()
    jobs = db.get_jobs(limit=1)
    
    if jobs:
        result = engine.analyze_and_draft(jobs[0]['id'])
        print(f"\nAnalysis Result:")
        print(f"Job: {result['title']} at {result['company']}")
        print(f"Score: {result['score']:.1f}/100")
        print(f"Rationale: {result['rationale']}")
        if result.get('cover_letter'):
            print(f"\nCover Letter:\n{result['cover_letter']}")
    else:
        print("No jobs in database to analyze")


if __name__ == "__main__":
    main()
