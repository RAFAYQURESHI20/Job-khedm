# JobPulse — Intelligent Job Aggregation Platform

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Production-brightgreen)

> An end-to-end job market intelligence platform that scrapes, classifies, and serves structured job listings through a modern REST API and dashboard.

---

## 📌 Overview

**JobPulse** automates the discovery and aggregation of job postings from multiple online sources. It normalizes raw listing data using an ML classification pipeline, stores results in a PostgreSQL database, and exposes everything through a FastAPI backend consumed by a React frontend dashboard.

Key capabilities:
- Multi-source scraping with rotating proxy support
- NLP-based job category classification (BERT fine-tuned)
- Automated daily pipeline via GitHub Actions + cron
- REST API with filtering, pagination, and export
- Real-time dashboard with search and analytics

---

## 🗂️ Project Structure

```
JobPulse/
├── .github/workflows/          # CI/CD and scheduled automation
│   ├── daily_pipeline.yml
│   └── deploy.yml
├── backend/                    # FastAPI application
│   ├── api/                    # Route handlers
│   ├── services/               # Business logic
│   └── models/                 # SQLAlchemy ORM models
├── frontend/                   # React dashboard
│   └── src/
│       ├── components/
│       ├── pages/
│       └── utils/
├── ml/                         # Machine learning pipeline
│   ├── models/
│   ├── training/
│   └── evaluation/
├── scrapers/                   # Scraping engine
│   ├── parsers/
│   └── exporters/
├── data/raw/                   # Raw scrape outputs (gitignored)
├── config.py                   # Central config / env loader
├── models.py                   # Shared Pydantic schemas
├── base_scraper.py             # Abstract scraper base class
├── final_scraper.py            # Production multi-source scraper
├── run_daily_pipeline.py       # Pipeline orchestrator
├── requirements.txt
├── Dockerfile
├── render.yaml
├── vercel.json
└── .env.example
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 15+
- Redis (optional, for caching)

### 1. Clone & install

```bash
git clone https://github.com/your-username/JobPulse.git
cd JobPulse
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your DB URL, API keys, proxy settings
```

### 3. Run the scraper

```bash
python final_scraper.py
```

### 4. Start the API

```bash
uvicorn backend.api.main:app --reload --port 8000
```

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 🤖 ML Pipeline

The classification model is a fine-tuned `distilbert-base-uncased` trained on ~45,000 labeled job postings across 18 categories (Engineering, Marketing, Finance, Healthcare, etc.).

Training:
```bash
python ml/training/train.py --epochs 5 --batch-size 32
```

Evaluation:
```bash
python ml/evaluation/evaluate.py --model-path ml/models/classifier_v3.pt
```

---

## 🚀 Deployment

### Render (Backend)
The `render.yaml` is pre-configured. Connect the repo in Render dashboard and deploy.

### Vercel (Frontend)
The `vercel.json` is pre-configured. Import the project in Vercel and set env vars.

### Docker
```bash
docker build -t jobpulse .
docker run -p 8000:8000 --env-file .env jobpulse
```

---

## 📅 Daily Automation

GitHub Actions runs the full pipeline every day at 02:00 UTC:
1. Scrape all configured sources
2. Classify new listings via ML model
3. Deduplicate & upsert to database
4. Send summary report to Slack webhook

See `.github/workflows/daily_pipeline.yml` for full config.

---

## 📄 License

MIT © 2025 JobPulse Contributors
