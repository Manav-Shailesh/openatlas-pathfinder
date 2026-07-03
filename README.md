# OpenATLAS Pathfinder

AI Threat Modeling & Attack Path Generation Platform — maps AI system
architectures to MITRE ATLAS techniques, generates attack paths, scores
risk, and produces mitigation reports.

## Setup

1. Create a virtual environment:
(python -m venv venv)

(source venv/bin/activate)   # Windows: (venv\Scripts\activate)

2. Install dependencies:
(pip install -r requirements.txt)

3. Copy `.env.example` to `.env` (cp .env.example .env) and set your MongoDB URI:

4. Make sure MongoDB is running locally (or use a MongoDB Atlas URI).
5. Run the test suite: (pytest tests/ -v)
6. Launch the app: (streamlit run app/main.py)

## Project Status
Phase 1 — project structure, config, and MongoDB connection layer complete.