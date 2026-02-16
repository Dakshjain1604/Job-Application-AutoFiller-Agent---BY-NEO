# AutoCareer - User Guide

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.8+
- Node.js 16+
- OpenAI API Key (get from [OpenAI Platform](https://platform.openai.com/api-keys))

### Running the Application

**Start Backend:**
```bash
cd /root/jobApplicationAutoFiller/backend
source ../venv/bin/activate
python main.py
```

**Start Frontend (in new terminal):**
```bash
cd /root/jobApplicationAutoFiller/frontend
npm start
```

**Access:** http://localhost:3000

---

## 📋 Step-by-Step Usage

### 1. Configure API Key (Required for Best Results)
1. Click the **Settings** button (top-right, gear icon)
2. Enter your **OpenAI API Key** (starts with `sk-...`)
3. Select model:
   - **GPT-4o**: Highest quality for cover letters
   - **GPT-4o Mini**: Best balance (recommended)
   - **GPT-3.5 Turbo**: Fastest/cheapest
4. Click **Save Settings**

💡 Your API key is stored locally in your browser only - never sent to third parties.

---

### 2. Upload Resume
1. Go to **Configuration** tab
2. Click **Upload Resume** and select your PDF
3. Wait for parsing (extracts name, email, skills, experience)
4. Verify profile information appears with green checkmark

---

### 3. Search for Jobs
1. Enter **Job Title Keywords**: `Machine Learning Engineer, Data Scientist, AI Researcher`
2. Set **Salary Range** (optional): Min: `100000`, Max: `150000`
3. Click **Search Jobs**
4. Wait 30-60 seconds for scraper to discover positions from:
   - LinkedIn (remote jobs worldwide)
   - Greenhouse (8+ tech company boards)

---

### 4. Analyze Job Fit
1. Navigate to **Job Board** tab
2. Browse discovered positions
3. Click **Analyze Fit** on interesting jobs
4. View AI-generated fit score (0-100) with detailed rationale:
   - Technical skills match
   - Experience level alignment
   - Domain expertise assessment
   - Required vs nice-to-have breakdown

**Scoring Rubric:**
- 90-100: Exceptional fit
- 75-89: Strong fit
- 60-74: Good fit
- 40-59: Moderate fit
- 0-39: Poor fit

---

### 5. Generate Cover Letter
1. For high-scoring jobs (60+), click **Generate Draft**
2. AI creates a persuasive, customized cover letter with:
   - Compelling opening hook
   - 2-3 specific achievements matching job requirements
   - Company-specific references (if available)
   - Professional call-to-action
3. Draft automatically saved to database

---

### 6. Review & Edit Draft
1. Go to **Review Queue** tab
2. Review the AI-generated cover letter
3. Edit directly in the text area:
   - Add personal anecdotes
   - Fix any inaccuracies
   - Adjust tone if needed
4. View word count (aim for 250-350 words)
5. Click **Save Changes** to update

**Tips for Strong Cover Letters:**
- Highlight specific achievements with metrics
- Reference company values or recent initiatives
- Keep it concise and proofread carefully

---

### 7. Submit Application (Dry Run)
1. After editing, click **Submit Application (Dry Run)**
2. Browser automation will:
   - Navigate to job posting
   - Detect form fields (name, email, phone, links, cover letter)
   - Fill detected fields with your data
   - Take screenshot for review
   - **NOT actually submit** (safe testing)
3. Review the results:
   - Fields detected count
   - Fields successfully filled
   - Screenshot path

---

### 8. Track Applications
1. Visit **Activity Log** tab
2. View all submissions with:
   - Timestamp
   - Company name
   - Action taken
   - Status (success/pending/error)
   - Link to job posting
3. Use for follow-up tracking

---

## 🎯 Key Features Explained

### Intelligent Scoring
- Uses GPT-4o-mini with 4-dimension evaluation framework
- Analyzes technical skills, experience, domain expertise, requirements match
- Provides specific matching skills and gap analysis
- Fallback to keyword-based scoring if no API key

### Persuasive Drafting
- Uses GPT-4o for highest quality writing
- Achievement-focused with specific examples
- Avoids clichés and generic statements
- Company research via RAG (website scraping)
- Fallback to template-based generation if no API key

### Smart Form Automation
- Detects common form fields automatically
- Separates LinkedIn/GitHub/Portfolio URLs intelligently
- Validates field filling success
- Screenshot + mapping report for verification
- Dry-run mode prevents accidental submissions

---

## 🔒 Privacy & Security

✅ **Local-first architecture**
- All data stored in SQLite database on your machine
- Vector embeddings stored locally (FAISS)
- No cloud uploads or third-party data sharing

✅ **API key security**
- Stored in browser localStorage only
- Never transmitted to any server except OpenAI directly
- Can be cleared anytime via Settings

✅ **Manual control**
- Review gate before every submission
- Dry-run mode for safe testing
- Edit all AI-generated content

---

## 🐛 Common Issues

### "Cannot connect to backend"
- Ensure backend is running: `python main.py` in backend directory
- Check backend logs for errors
- Verify port 8000 is available

### "No jobs found"
- Try broader keywords: "Machine Learning" instead of "Senior ML Engineer"
- LinkedIn/Greenhouse may have rate limits - wait and retry
- Check backend logs for scraper errors

### "API key invalid"
- Get key from https://platform.openai.com/api-keys
- Ensure key starts with `sk-`
- Check OpenAI account has credits

### Cover letter too generic
- Ensure API key is configured (Settings)
- Try GPT-4o model for highest quality
- Manually edit to add personal touches

### Form automation not working
- Different sites have different structures
- Dry-run shows what fields were detected
- May require manual submission for complex forms

---

## 💰 API Costs

**Estimated costs per job application:**
- Job scoring (GPT-4o-mini): $0.001 - $0.003
- Cover letter (GPT-4o): $0.01 - $0.03
- **Total per application: ~$0.02 - $0.04**

**For 50 applications: ~$1-2**

💡 Use GPT-3.5-turbo to reduce costs further (lower quality).

---

## 📞 Need Help?

1. Check this guide thoroughly
2. Review backend logs: `tail -f /root/jobApplicationAutoFiller/backend.log`
3. Check frontend console: Open browser DevTools (F12)
4. Review API documentation: http://localhost:8000/docs

---

**Good luck with your job search! 🎯**
