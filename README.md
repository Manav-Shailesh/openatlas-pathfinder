# 🛡️ OpenATLAS Pathfinder

**AI Threat Modeling & Attack Path Generation Platform**

An open-source, free alternative to expensive enterprise AI security tools. OpenATLAS Pathfinder accepts AI system architecture descriptions, documents, and diagrams and automatically maps them to MITRE ATLAS v2026.06 — generating realistic attack paths, risk scores, and mitigation recommendations.

---

## 🎯 What It Does

| Step | What Happens |
|---|---|
| 1 | User uploads PDF, TXT, Markdown or architecture diagram (PNG/JPG) |
| 2 | System detects AI components — LLM, RAG, Agent, Tool Calling, Memory, MCP, Vector DB |
| 3 | Components are mapped to MITRE ATLAS v2026.06 tactics and techniques |
| 4 | Google Gemini AI reasons about realistic multi-step attack chains |
| 5 | Each path is scored using Likelihood × Impact × Exposure |
| 6 | Gemini generates specific, actionable mitigations per path |
| 7 | Results rendered as interactive graph, risk heatmap, and downloadable PDF report |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or 3.12
- MongoDB running locally (or a MongoDB Atlas URI)
- A free Google Gemini API key from [aistudio.google.com](https://aistudio.google.com/app/apikey)

### 1 — Clone the repository

```bash
git clone https://github.com/yourusername/openatlas-pathfinder.git
cd openatlas-pathfinder
```

### 2 — Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=openatlas_pathfinder
APP_ENV=development
GOOGLE_API_KEY=your_free_gemini_api_key_here
```

### 5 — Start MongoDB

```bash
# Windows
net start MongoDB

# Mac
brew services start mongodb-community

# Linux
sudo systemctl start mongod
```

### 6 — Run the application

```bash
streamlit run app/main.py
```

Open your browser at **http://localhost:8501**

---

## 📁 Project Structure

```
openatlas-pathfinder/
│
├── app/
│   ├── main.py                          # Streamlit entrypoint
│   ├── config.py                        # Settings and environment variables
│   │
│   ├── db/
│   │   ├── mongo_client.py              # MongoDB connection singleton
│   │   └── schemas.py                   # Pydantic models for all collections
│   │
│   ├── models/
│   │   └── enums.py                     # Shared enums (ComponentType, RiskLevel)
│   │
│   ├── ingestion/
│   │   ├── extractors.py                # PDF / TXT / MD text extraction
│   │   ├── component_detector.py        # Keyword/regex AI component detection
│   │   ├── diagram_extractor.py         # Gemini Vision diagram understanding
│   │   └── service.py                   # Ingestion pipeline orchestrator
│   │
│   ├── atlas_mapping/
│   │   ├── atlas_loader.py              # Loads and caches ATLAS.yaml
│   │   └── mapper.py                    # Maps components → ATLAS techniques
│   │
│   ├── attack_paths/
│   │   ├── ai_path_generator.py         # Gemini AI attack chain generation
│   │   ├── graph_builder.py             # NetworkX + PyVis graph builder
│   │   ├── risk_scorer.py               # Gemini risk scoring + L×I×E formula
│   │   ├── mitigation_engine.py         # Gemini mitigation generation
│   │   └── service.py                   # Attack path pipeline orchestrator
│   │
│   ├── risk_scoring/                    # Phase 6 — Risk dashboard
│   ├── visualization/                   # Phase 7 — Charts and heatmaps
│   ├── reports/                         # Phase 8 — PDF report generator
│   │
│   └── pages/
│       ├── 1_Upload.py                  # Upload architecture document
│       ├── 2_Analysis.py                # MITRE ATLAS technique mapping
│       ├── 3_Attack_Paths.py            # AI-generated attack paths + graph
│       ├── 4_Risk_Dashboard.py          # Risk heatmap and scoring summary
│       └── 5_Report_Export.py           # PDF report download
│
├── data/
│   ├── atlas_knowledge_base/
│   │   ├── ATLAS.yaml                   # MITRE ATLAS v2026.06 full dataset
│   │   └── component_technique_map.json # Component → technique ID lookup
│   └── sample_docs/
│       ├── sample_architecture.txt      # Sample text architecture description
│       └── sample_diagram.png           # Sample architecture diagram
│
├── tests/
│   ├── test_db_connection.py            # Phase 1 — DB connection tests
│   ├── test_extractors.py               # Phase 2 — Text extraction tests
│   ├── test_component_detector.py       # Phase 2 — Component detection tests
│   ├── test_diagram_extractor.py        # Phase 2.5 — Diagram extraction tests
│   ├── test_atlas_mapper.py             # Phase 4 — ATLAS mapping tests
│   └── test_attack_paths.py             # Phase 5 — Attack path tests
│
├── .env.example                         # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🧩 Tech Stack

| Category | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | Python 3.12 |
| Database | MongoDB + PyMongo |
| AI / Vision | Google Gemini API (free tier) |
| Threat Framework | MITRE ATLAS v2026.06 |
| Graph Analysis | NetworkX |
| Graph Visualization | PyVis |
| Charts | Plotly |
| PDF Parsing | pdfplumber |
| PDF Generation | ReportLab |
| Data Validation | Pydantic v2 |
| Testing | pytest |

---

## 🔑 Getting a Free Gemini API Key

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with any Google account
3. Click **Create API Key**
4. Copy it into your `.env` file as `GOOGLE_API_KEY=...`

**Free tier limits:** 1,500 requests/day · 1M token context window · No credit card required

---

## 🗺️ Development Phases

| Phase | Status | Description |
|---|---|---|
| Phase 1 | ✅ Complete | Project structure, config, MongoDB connection |
| Phase 2 | ✅ Complete | Document ingestion — PDF, TXT, Markdown |
| Phase 2.5 | ✅ Complete | Diagram understanding — Gemini Vision API |
| Phase 3 | ✅ Complete | Architecture understanding engine |
| Phase 4 | ✅ Complete | MITRE ATLAS mapping engine |
| Phase 5 | ✅ Complete | AI attack path generation — Gemini reasoning |
| Phase 6 | 🔄 In Progress | Risk scoring dashboard |
| Phase 7 | 🔄 In Progress | Visualization engine |
| Phase 8 | 🔄 In Progress | PDF report generator |

---

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run a specific phase
pytest tests/test_db_connection.py -v
pytest tests/test_extractors.py -v
pytest tests/test_component_detector.py -v
pytest tests/test_atlas_mapper.py -v
pytest tests/test_attack_paths.py -v

# Skip live API tests (no API key needed)
pytest tests/ -v -k "not requires_api_key"
```

---

## 📋 Sample Input

Try this text as a quick test. Upload it on the **Upload** page:

```
Our system uses GPT-4 as the core LLM with a RAG pipeline backed by
Pinecone as the vector database. We use Agent Memory to persist
conversation history across sessions. Tool Calling is enabled for
Gmail Integration and Slack Integration. The agent can autonomously
decide which tool to call based on user intent. We also use an MCP
server for external tool connections.
```

**Expected detected components:** LLM, RAG, Vector Database, Memory, Tool Calling, External API, MCP

**Expected ATLAS techniques:** Prompt Injection, RAG Poisoning, Tool Invocation, Context Poisoning, Data Exfiltration, and more

---

## 📊 How Risk is Scored

```
Risk Score = (Likelihood × Impact × Exposure) / 10

Range       Level
0  – 30     🟢 Low
31 – 60     🟡 Medium
61 – 100    🔴 High
```

- **Likelihood** — How easy is this attack to execute in practice (1–10)
- **Impact** — How severe is the business damage if successful (1–10)
- **Exposure** — How exposed is this specific architecture to this path (1–10)

Scores are generated by Google Gemini with a written explanation specific to your architecture — not just a generic formula.

---

## 🤖 AI-Powered Attack Path Generation

This is not a rule-based lookup table. The system uses Gemini to **reason** about realistic attack chains:

1. Detected components and mapped ATLAS techniques are sent to Gemini with a structured prompt
2. Gemini generates 3–5 unique, architecture-specific multi-step attack paths
3. Every returned technique ID is validated against the local ATLAS.yaml — hallucinated IDs are discarded
4. Paths with fewer than 2 valid steps are discarded and replaced by rule-based fallbacks
5. Gemini then scores each path and generates specific mitigations

This means two different architectures will always produce different attack paths, even if they share some of the same components.

---

## 🛡️ Detected Components

| Component Type | Example Keywords Detected |
|---|---|
| LLM | GPT-4, Claude, Gemini, Llama, large language model |
| RAG | RAG, retrieval augmented generation |
| Vector Database | Pinecone, Weaviate, Chroma, Qdrant, FAISS, vector store |
| Agent | agent, autonomous agent, agentic |
| Tool Calling | tool calling, function calling, tool use |
| Memory | agent memory, memory, conversation history |
| External API | Gmail, Slack, external API, third-party API |
| Plugin | plugin, extension |
| MCP | MCP, model context protocol |
| Knowledge Base | knowledge base, document store |

---

## ⚠️ Important Disclaimer

OpenATLAS Pathfinder is a **threat modeling tool only**.

- It does NOT perform live penetration testing
- It does NOT exploit vulnerabilities
- It does NOT scan live systems
- It is designed for pre-deployment security review of AI architecture designs

---

## 🗂️ MongoDB Collections

| Collection | Purpose |
|---|---|
| `analyses` | Stores uploaded file info, extracted text, and detected components |
| `attack_path_records` | Stores AI-generated attack paths, risk scores, and mitigations |
| `health_checks` | Used by Phase 1 tests to verify DB connectivity |

---

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 🙏 Acknowledgements

- [MITRE ATLAS](https://atlas.mitre.org/) — Adversarial Threat Landscape for AI Systems
- [Google Gemini](https://aistudio.google.com/) — Free Vision and reasoning API
- [Streamlit](https://streamlit.io/) — Open-source Python web framework
- [NetworkX](https://networkx.org/) — Graph analysis library
- [PyVis](https://pyvis.readthedocs.io/) — Interactive network visualization

---

*Built as an MSc Cybersecurity project — open-source, free, and community-driven.*