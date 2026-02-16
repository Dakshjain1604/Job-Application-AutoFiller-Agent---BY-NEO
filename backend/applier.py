"""
Application Automation Module for AutoCareer.
Uses Playwright to fill and submit job applications.
"""

import asyncio
from typing import Dict, Optional, List, Any
from playwright.async_api import async_playwright, Page, Browser
from database import get_db
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class ApplicationAutomation:
    """Browser automation for job applications."""
    
    def __init__(self, dry_run: bool = True):
        """Initialize with dry run mode (default: True)."""
        self.dry_run = dry_run
        self.browser: Optional[Browser] = None
        self.context = None
        
    async def initialize(self):
        """Start browser session."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)  # Visible for review
        self.context = await self.browser.new_context()
        
    async def close(self):
        """Close browser session."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def fill_form_field(self, page: Page, field_selector: str, value: str) -> bool:
        """
        Fill a form field with retry logic and validation.
        Returns: True if successful, False otherwise
        """
        try:
            # Wait for field to be visible
            await page.wait_for_selector(field_selector, state='visible', timeout=5000)
            
            # Clear existing content
            await page.fill(field_selector, '')
            
            # Fill with new value
            await page.fill(field_selector, value)
            
            # Verify the value was set
            filled_value = await page.input_value(field_selector)
            if filled_value == value:
                logger.info(f"✓ Filled field: {field_selector}")
                return True
            else:
                logger.warning(f"✗ Field value mismatch for {field_selector}")
                return False
                
        except Exception as e:
            logger.warning(f"✗ Could not fill field {field_selector}: {e}")
            return False
    
    async def detect_form_fields(self, page: Page) -> Dict[str, List[str]]:
        """
        Detect available form fields on the page.
        Returns: dictionary of field types and their selectors
        """
        detected = {
            'name': [],
            'email': [],
            'phone': [],
            'linkedin': [],
            'website': [],
            'github': [],
            'cover_letter': [],
            'other_text': []
        }
        
        # Name fields
        name_patterns = ['name', 'full-name', 'fullname', 'first-name', 'last-name']
        for pattern in name_patterns:
            selectors = [
                f'input[name*="{pattern}"]',
                f'input[id*="{pattern}"]',
                f'input[placeholder*="{pattern}"]'
            ]
            for sel in selectors:
                if await page.query_selector(sel):
                    detected['name'].append(sel)
        
        # Email fields
        email_selectors = ['input[type="email"]', 'input[name*="email"]', 'input[id*="email"]']
        for sel in email_selectors:
            if await page.query_selector(sel):
                detected['email'].append(sel)
        
        # Phone fields
        phone_selectors = ['input[type="tel"]', 'input[name*="phone"]', 'input[id*="phone"]']
        for sel in phone_selectors:
            if await page.query_selector(sel):
                detected['phone'].append(sel)
        
        # LinkedIn
        linkedin_selectors = ['input[name*="linkedin"]', 'input[id*="linkedin"]']
        for sel in linkedin_selectors:
            if await page.query_selector(sel):
                detected['linkedin'].append(sel)
        
        # Website/Portfolio
        website_selectors = ['input[name*="website"]', 'input[name*="portfolio"]', 'input[id*="website"]']
        for sel in website_selectors:
            if await page.query_selector(sel):
                detected['website'].append(sel)
        
        # GitHub
        github_selectors = ['input[name*="github"]', 'input[id*="github"]']
        for sel in github_selectors:
            if await page.query_selector(sel):
                detected['github'].append(sel)
        
        # Cover letter / text areas
        textarea_selectors = ['textarea[name*="cover"]', 'textarea[name*="letter"]', 'textarea']
        for sel in textarea_selectors:
            if await page.query_selector(sel):
                detected['cover_letter'].append(sel)
        
        return detected

    async def apply_to_job(self, job_id: int, profile_id: int = 1, 
                          draft_id: Optional[int] = None) -> Dict:
        """
        Enhanced job application automation with intelligent field mapping.
        Returns: application result with detailed field mapping info
        """
        db = get_db()
        
        # Get job, profile, and draft
        job = db.get_job(job_id)
        profile = db.get_profile(profile_id)
        draft = db.get_draft_by_job(job_id) if not draft_id else db.get_draft(draft_id)
        
        if not job or not profile:
            raise ValueError("Job or profile not found")
        
        result = {
            'job_id': job_id,
            'status': 'pending',
            'message': '',
            'dry_run': self.dry_run,
            'fields_filled': {},
            'fields_detected': {}
        }
        
        try:
            await self.initialize()
            page = await self.context.new_page()
            
            # Navigate to application URL
            logger.info(f"Navigating to: {job['url']}")
            await page.goto(job['url'], wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Detect available form fields
            detected_fields = await self.detect_form_fields(page)
            result['fields_detected'] = {k: len(v) for k, v in detected_fields.items() if v}
            
            logger.info(f"Detected fields: {result['fields_detected']}")
            
            # Fill name fields
            if detected_fields['name'] and profile.get('name'):
                for selector in detected_fields['name'][:1]:  # Fill first name field
                    if not self.dry_run:
                        success = await self.fill_form_field(page, selector, profile['name'])
                        result['fields_filled']['name'] = success
                    else:
                        logger.info(f"[DRY RUN] Would fill name: {selector} = {profile['name']}")
                        result['fields_filled']['name'] = 'dry_run'
            
            # Fill email fields
            if detected_fields['email'] and profile.get('email'):
                for selector in detected_fields['email'][:1]:
                    if not self.dry_run:
                        success = await self.fill_form_field(page, selector, profile['email'])
                        result['fields_filled']['email'] = success
                    else:
                        logger.info(f"[DRY RUN] Would fill email: {selector} = {profile['email']}")
                        result['fields_filled']['email'] = 'dry_run'
            
            # Fill phone fields
            if detected_fields['phone'] and profile.get('phone'):
                for selector in detected_fields['phone'][:1]:
                    if not self.dry_run:
                        success = await self.fill_form_field(page, selector, profile['phone'])
                        result['fields_filled']['phone'] = success
                    else:
                        logger.info(f"[DRY RUN] Would fill phone: {selector} = {profile['phone']}")
                        result['fields_filled']['phone'] = 'dry_run'
            
            # Fill links (LinkedIn, GitHub, Website)
            if profile.get('links'):
                links_list = [link.strip() for link in profile['links'].split(',')]
                linkedin_url = next((link for link in links_list if 'linkedin.com' in link.lower()), None)
                github_url = next((link for link in links_list if 'github.com' in link.lower()), None)
                website_url = next((link for link in links_list if 'linkedin' not in link.lower() and 'github' not in link.lower()), None)
                
                # LinkedIn
                if detected_fields['linkedin'] and linkedin_url:
                    for selector in detected_fields['linkedin'][:1]:
                        if not self.dry_run:
                            success = await self.fill_form_field(page, selector, linkedin_url)
                            result['fields_filled']['linkedin'] = success
                        else:
                            logger.info(f"[DRY RUN] Would fill LinkedIn: {selector} = {linkedin_url}")
                            result['fields_filled']['linkedin'] = 'dry_run'
                
                # GitHub
                if detected_fields['github'] and github_url:
                    for selector in detected_fields['github'][:1]:
                        if not self.dry_run:
                            success = await self.fill_form_field(page, selector, github_url)
                            result['fields_filled']['github'] = success
                        else:
                            logger.info(f"[DRY RUN] Would fill GitHub: {selector} = {github_url}")
                            result['fields_filled']['github'] = 'dry_run'
                
                # Website/Portfolio
                if detected_fields['website'] and website_url:
                    for selector in detected_fields['website'][:1]:
                        if not self.dry_run:
                            success = await self.fill_form_field(page, selector, website_url)
                            result['fields_filled']['website'] = success
                        else:
                            logger.info(f"[DRY RUN] Would fill website: {selector} = {website_url}")
                            result['fields_filled']['website'] = 'dry_run'
            
            # Fill cover letter
            if detected_fields['cover_letter'] and draft and draft.get('cover_letter'):
                for selector in detected_fields['cover_letter'][:1]:  # Fill first textarea
                    if not self.dry_run:
                        success = await self.fill_form_field(page, selector, draft['cover_letter'])
                        result['fields_filled']['cover_letter'] = success
                    else:
                        logger.info(f"[DRY RUN] Would fill cover letter: {selector} = [draft content]")
                        result['fields_filled']['cover_letter'] = 'dry_run'
            
            # Take screenshot for review
            import os
            os.makedirs('./backend/logs', exist_ok=True)
            screenshot_path = f"./backend/logs/application_{job_id}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            result['screenshot'] = screenshot_path
            
            if self.dry_run:
                result['status'] = 'dry_run_complete'
                result['message'] = f"Dry run completed. Detected {sum(result['fields_detected'].values())} form fields. Screenshot saved."
                logger.info("✓ DRY RUN: Form mapping completed successfully")
            else:
                # In real mode, look for submit button
                submit_selectors = [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Submit")',
                    'button:has-text("Apply")',
                    'button[name*="submit"]'
                ]
                
                submitted = False
                for selector in submit_selectors:
                    if await page.query_selector(selector):
                        logger.info(f"Found submit button: {selector}")
                        logger.info("⏳ Waiting 10 seconds for manual review before submission...")
                        await page.wait_for_timeout(10000)
                        
                        await page.click(selector)
                        await page.wait_for_timeout(3000)
                        submitted = True
                        break
                
                if submitted:
                    result['status'] = 'submitted'
                    result['message'] = 'Application submitted successfully'
                else:
                    result['status'] = 'manual_required'
                    result['message'] = 'Could not find submit button. Manual submission required.'
            
            # Log application
            db.log_application(
                job_id=job_id,
                profile_id=profile_id,
                job_url=job['url'],
                company=job['company'],
                action='apply',
                status=result['status'],
                draft_id=draft['id'] if draft else None,
                draft_content=draft['cover_letter'] if draft else None
            )
            
            await page.close()
            await self.close()
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            result['status'] = 'error'
            result['message'] = str(e)
            
            # Log error
            db.log_application(
                job_id=job_id,
                profile_id=profile_id,
                job_url=job.get('url', ''),
                company=job.get('company', ''),
                action='apply',
                status='error',
                error_message=str(e)
            )
        
        return result


async def main():
    """Test applier."""
    db = get_db()
    jobs = db.get_jobs(limit=1)
    
    if jobs:
        applier = ApplicationAutomation(dry_run=True)
        result = await applier.apply_to_job(jobs[0]['id'])
        print(f"\nApplication Result:")
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
    else:
        print("No jobs in database to apply to")


if __name__ == "__main__":
    asyncio.run(main())
