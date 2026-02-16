"""
Job Discovery Module for AutoCareer.
Scrapes LinkedIn and Greenhouse for remote ML/technical roles.
"""

import asyncio
import re
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
from database import get_db
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class JobScraper:
    """Web scraper for job postings."""
    
    def __init__(self):
        """Initialize scraper."""
        self.browser: Optional[Browser] = None
        self.context = None
        
    async def initialize(self):
        """Start browser session."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        
    async def close(self):
        """Close browser session."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    def parse_salary(self, salary_text: str) -> tuple:
        """Extract min and max salary from text."""
        if not salary_text:
            return None, None
        
        # Look for patterns like "$100k-$150k" or "$100,000 - $150,000"
        numbers = re.findall(r'\$?(\d{1,3}(?:,?\d{3})*(?:k|K)?)', salary_text)
        
        salaries = []
        for num in numbers:
            num = num.replace(',', '')
            if 'k' in num.lower():
                num = num.lower().replace('k', '000')
            try:
                salaries.append(int(num))
            except:
                continue
        
        if len(salaries) >= 2:
            return min(salaries), max(salaries)
        elif len(salaries) == 1:
            return salaries[0], salaries[0]
        
        return None, None
    
    async def scrape_linkedin(self, keywords: str, max_jobs: int = 25) -> List[Dict]:
        """
        Scrape LinkedIn for jobs matching keywords.
        Enhanced with better selectors and error handling.
        """
        jobs = []
        
        try:
            page = await self.context.new_page()
            
            # Search URL (remote jobs, worldwide)
            keywords_encoded = keywords.replace(' ', '%20')
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords_encoded}&location=Worldwide&f_WT=2"
            
            logger.info(f"Scraping LinkedIn with keywords: {keywords}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for content to load
            try:
                await page.wait_for_selector('.jobs-search__results-list', timeout=10000)
            except:
                logger.warning("LinkedIn jobs list not found, trying alternative selectors")
            
            await page.wait_for_timeout(3000)
            
            # Scroll to load more jobs
            for _ in range(3):
                await page.evaluate('window.scrollBy(0, window.innerHeight)')
                await page.wait_for_timeout(1000)
            
            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find job cards with multiple selector patterns
            job_cards = []
            selectors = [
                'div.base-card',
                'div.job-search-card',
                'li.jobs-search-results__list-item',
                'div[data-job-id]'
            ]
            
            for selector in selectors:
                cards = soup.select(selector)
                if cards:
                    job_cards.extend(cards)
                    break
            
            logger.info(f"Found {len(job_cards)} job cards on LinkedIn")
            
            for card in job_cards[:max_jobs]:
                try:
                    # Try multiple selector patterns for title
                    title = None
                    title_selectors = [
                        'h3.base-search-card__title',
                        'h3.job-search-card__title',
                        'a.job-card-list__title',
                        'span.sr-only'
                    ]
                    for sel in title_selectors:
                        elem = card.select_one(sel)
                        if elem:
                            title = elem.get_text(strip=True)
                            break
                    
                    # Try multiple selector patterns for company
                    company = None
                    company_selectors = [
                        'h4.base-search-card__subtitle',
                        'h4.job-search-card__company-name',
                        'a.job-card-container__company-name',
                        'span.job-card-container__primary-description'
                    ]
                    for sel in company_selectors:
                        elem = card.select_one(sel)
                        if elem:
                            company = elem.get_text(strip=True)
                            break
                    
                    # Location
                    location = "Remote"
                    location_selectors = [
                        'span.job-search-card__location',
                        'span.job-card-container__metadata-item',
                    ]
                    for sel in location_selectors:
                        elem = card.select_one(sel)
                        if elem:
                            location = elem.get_text(strip=True)
                            break
                    
                    # Job URL
                    url = None
                    link_elem = card.find('a', href=True)
                    if link_elem:
                        url = link_elem.get('href', '')
                        # Make absolute URL
                        if url.startswith('/'):
                            url = 'https://www.linkedin.com' + url
                        # Clean URL
                        if '?' in url:
                            url = url.split('?')[0]
                    
                    if title and company and url:
                        jobs.append({
                            'title': title,
                            'company': company,
                            'location': location,
                            'url': url,
                            'source': 'LinkedIn',
                            'description': '',
                            'requirements': '',
                            'salary_min': None,
                            'salary_max': None
                        })
                        
                        logger.info(f"Scraped: {title} at {company}")
                
                except Exception as e:
                    logger.error(f"Error parsing LinkedIn job card: {e}")
                    continue
            
            await page.close()
            
        except Exception as e:
            logger.error(f"LinkedIn scraping error: {e}")
        
        return jobs
    
    async def scrape_greenhouse(self, keywords: str, max_jobs: int = 25) -> List[Dict]:
        """
        Scrape Greenhouse job boards.
        Enhanced with more company boards and better filtering.
        """
        jobs = []
        
        # Expanded list of tech company Greenhouse boards
        greenhouse_boards = [
            "https://boards.greenhouse.io/embed/job_board?for=openai",
            "https://boards.greenhouse.io/embed/job_board?for=anthropic",
            "https://boards.greenhouse.io/embed/job_board?for=databricks",
            "https://boards.greenhouse.io/embed/job_board?for=scale",
            "https://boards.greenhouse.io/embed/job_board?for=modal",
            "https://boards.greenhouse.io/embed/job_board?for=cohere",
            "https://boards.greenhouse.io/embed/job_board?for=perplexity",
            "https://boards.greenhouse.io/embed/job_board?for=adept",
        ]
        
        try:
            page = await self.context.new_page()
            
            for board_url in greenhouse_boards:
                if len(jobs) >= max_jobs:
                    break
                    
                try:
                    logger.info(f"Scraping Greenhouse board: {board_url}")
                    await page.goto(board_url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Wait for job listings to load
                    try:
                        await page.wait_for_selector('.opening', timeout=5000)
                    except:
                        logger.warning(f"No jobs found on {board_url}")
                        continue
                    
                    await page.wait_for_timeout(2000)
                    
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract company name from URL
                    company_match = re.search(r'for=([^&]+)', board_url)
                    company = company_match.group(1).replace('-', ' ').title() if company_match else "Unknown"
                    
                    # Find job listings with multiple selector patterns
                    job_sections = soup.find_all(['div', 'section'], class_=re.compile('opening|job'))
                    
                    for section in job_sections[:max_jobs]:
                        try:
                            # Find link and title
                            link = section.find('a', href=re.compile('/jobs/'))
                            if not link:
                                continue
                            
                            title = link.get_text(strip=True)
                            url = link.get('href', '')
                            
                            # Make full URL if relative
                            if url.startswith('/'):
                                base_url = 'https://boards.greenhouse.io'
                                url = base_url + url
                            
                            # Find location if available
                            location = "Remote"
                            location_elem = section.find(['span', 'div'], class_=re.compile('location'))
                            if location_elem:
                                location = location_elem.get_text(strip=True)
                            
                            # Filter by keywords (case insensitive, partial match)
                            keyword_list = [kw.strip().lower() for kw in keywords.split(',')]
                            title_lower = title.lower()
                            
                            if any(kw in title_lower for kw in keyword_list):
                                jobs.append({
                                    'title': title,
                                    'company': company,
                                    'location': location,
                                    'url': url,
                                    'source': 'Greenhouse',
                                    'description': '',
                                    'requirements': '',
                                    'salary_min': None,
                                    'salary_max': None
                                })
                                
                                logger.info(f"Scraped: {title} at {company}")
                        
                        except Exception as e:
                            logger.error(f"Error parsing Greenhouse job: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"Error scraping Greenhouse board {board_url}: {e}")
                    continue
            
            await page.close()
            
        except Exception as e:
            logger.error(f"Greenhouse scraping error: {e}")
        
        return jobs
    
    async def get_job_details(self, url: str) -> Dict:
        """
        Fetch detailed job description from URL.
        Enhanced with better content extraction.
        """
        try:
            page = await self.context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract description with multiple selector patterns
            description = ""
            desc_selectors = [
                'div.description',
                'div.job-description',
                'div[class*="description"]',
                'div.content',
                'section[class*="description"]',
                'div#job-details',
                'article'
            ]
            
            for selector in desc_selectors:
                elem = soup.select_one(selector)
                if elem:
                    description = elem.get_text(separator='\n', strip=True)
                    break
            
            # Extract requirements section specifically
            requirements = ""
            req_keywords = ['requirements', 'qualifications', 'must have', 'you have', 'what you bring']
            
            for keyword in req_keywords:
                # Find headers containing the keyword
                headers = soup.find_all(['h2', 'h3', 'h4', 'strong', 'b'], string=re.compile(keyword, re.IGNORECASE))
                if headers:
                    # Get the content after the header
                    for header in headers:
                        next_elem = header.find_next(['ul', 'ol', 'div', 'p'])
                        if next_elem:
                            requirements += next_elem.get_text(separator='\n', strip=True) + '\n'
                    if requirements:
                        break
            
            await page.close()
            
            return {
                'description': description[:5000],  # Limit length
                'requirements': requirements[:2000] if requirements else ""
            }
            
        except Exception as e:
            logger.error(f"Error fetching job details from {url}: {e}")
            return {'description': '', 'requirements': ''}
    
    async def search_jobs(self, keywords: str, salary_range: tuple = None, max_jobs: int = 50) -> List[Dict]:
        """
        Main search method combining all sources.
        Returns list of job dictionaries.
        """
        await self.initialize()
        
        all_jobs = []
        
        # Scrape LinkedIn
        linkedin_jobs = await self.scrape_linkedin(keywords, max_jobs=max_jobs//2)
        all_jobs.extend(linkedin_jobs)
        
        # Scrape Greenhouse
        greenhouse_jobs = await self.scrape_greenhouse(keywords, max_jobs=max_jobs//2)
        all_jobs.extend(greenhouse_jobs)
        
        # Filter by salary if provided
        if salary_range:
            min_sal, max_sal = salary_range
            filtered_jobs = []
            for job in all_jobs:
                if job['salary_min'] and job['salary_max']:
                    # Check if job salary overlaps with target range
                    if (job['salary_min'] <= max_sal and job['salary_max'] >= min_sal):
                        filtered_jobs.append(job)
                else:
                    # Include jobs without salary info
                    filtered_jobs.append(job)
            all_jobs = filtered_jobs
        
        # Store in database
        db = get_db()
        for job in all_jobs:
            try:
                job_id = db.insert_job(
                    title=job['title'],
                    company=job['company'],
                    url=job['url'],
                    source=job['source'],
                    location=job.get('location'),
                    salary_min=job.get('salary_min'),
                    salary_max=job.get('salary_max'),
                    description=job.get('description'),
                    requirements=job.get('requirements')
                )
                job['id'] = job_id
            except Exception as e:
                logger.error(f"Error inserting job to DB: {e}")
        
        await self.close()
        
        logger.info(f"Total jobs scraped and stored: {len(all_jobs)}")
        return all_jobs


async def main():
    """Test scraper."""
    scraper = JobScraper()
    jobs = await scraper.search_jobs("Machine Learning Engineer", max_jobs=10)
    print(f"\nScraped {len(jobs)} jobs:")
    for job in jobs:
        print(f"- {job['title']} at {job['company']} ({job['source']})")


if __name__ == "__main__":
    asyncio.run(main())
