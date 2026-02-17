# 🚀 AutoCareer - Intelligent Job Application Automation

**Automated ML/Technical Role Applications with AI-Powered Matching & Smart Cover Letters**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18.2+-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Built by Neo](https://img.shields.io/badge/Built%20by-Neo%20AI%20Agent-blueviolet.svg)](https://github.com/Dakshjain1604)

> This project was built by **[NEO](https://heyneo.so/)**, an autonomous AI/ML agent, through 30 iterative development cycles — covering architecture, implementation, debugging, and documentation without human coding intervention.

---

## Overview

**AutoCareer** automates job applications for ML/technical roles using AI-powered matching, RAG-based cover letter generation, and browser automation. Built with React, FastAPI, and OpenAI GPT-4.

**Core capabilities:**
- **Resume Vectorization** — Parse PDFs, generate embeddings via SentenceTransformers, index with FAISS
- **Job Scraping** — Scrape LinkedIn and Greenhouse with anti-bot protection
- **Fit Scoring** — Keyword baseline + optional GPT-4 reasoning (0–100 score with rationale)
- **Cover Letter Generation** — RAG pipeline: scrape company site → retrieve context → generate draft
- **Browser Automation** — Auto-fill forms via Selenium with dry-run mode and a 10s review gate
- **Audit Trail** — SHA-256 hashed, immutable logs with screenshots

**Privacy-first:** All data stays local — SQLite, FAISS index, and credentials never leave your machine.

---

## Quick Start

### Docker (Recommended)

```bash
git clone <repository-url>
cd autocareer
docker-compose up --build
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Manual Setup

```bash
# Backend
cd backend
python3 -m venv ../venv && source ../venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # add OpenAI API key (optional)
python main.py

# Frontend
cd frontend
npm install && npm start
```

> OpenAI API key is optional — the system falls back to keyword-based scoring without it.

---

## Architecture

```
React Frontend (3000)
        │ REST API
FastAPI Backend (8000)
   ├── profile_engine.py   → PDF parsing, embeddings, FAISS index
   ├── scraper.py          → Playwright-based LinkedIn/Greenhouse scraper
   ├── intelligence.py     → GPT-4 scoring, LangChain RAG cover letters
   ├── applier.py          → Selenium form automation
   ├── database.py         → SQLAlchemy + SQLite
   └── main.py             → 11 REST endpoints
        │
SQLite + FAISS + Local Files
```

**Tech stack:** Python 3.10, FastAPI, React 18, Tailwind CSS, Playwright, Selenium, SentenceTransformers, FAISS, LangChain, OpenAI GPT-4, SQLite, Docker

---

## API Reference

| Endpoint | Method | Description |
| --- | --- | --- |
| `/upload-resume` | POST | Parse and vectorize resume PDF |
| `/search-jobs` | POST | Scrape jobs with keyword/salary filters |
| `/analyze-job/{id}` | POST | Generate fit score and rationale |
| `/generate-draft/{id}` | POST | RAG-based cover letter |
| `/draft/{id}` | PUT | Edit draft content |
| `/submit-application/{id}` | POST | Submit (dry-run or real) |
| `/jobs` | GET | List all scraped jobs |
| `/application-logs` | GET | Audit trail |
| `/health` | GET | Health check |

Full docs at `http://localhost:8000/docs`

---

## Extending This Project using NEO

This codebase is modular and straightforward to expand:

- **New job boards** — Add a scraper method in `scraper.py` following the existing Playwright pattern
- **Better scoring** — Swap the GPT-4 prompt in `intelligence.py` with a fine-tuned classifier or local LLM
- **Smarter RAG** — Replace the flat FAISS index with HNSW for larger corpora, or add semantic caching to reuse company embeddings
- **Live resume feedback** — Add an endpoint that compares resume embeddings against a batch of job descriptions to surface skill gaps
- **Scale out** — Replace SQLite with PostgreSQL and FAISS with Pinecone when moving beyond local use
- **Retry logic** — Add exponential backoff and circuit breakers in `applier.py` for more resilient form submission

---

## Troubleshooting

| Issue | Fix |
| --- | --- |
| `OpenAI API key not found` | Expected — falls back to keyword scoring. Add key to `backend/.env` to enable LLM features |
| `FAISS index not found` | Upload a resume first via `/upload-resume` |
| `LinkedIn login expired` | Delete `backend/cookies/` and re-authenticate |
| Docker build fails | Run `docker system prune -a` then `docker-compose up --build` |

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built by **[NEO](https://heyneo.so/)** — an autonomous AI agent. More of Neo's work: [Medical Report Analysis Pipeline](https://github.com/dakshjain-1616/Medical-Report-Analysis-Pipeline-by-Neo).*
