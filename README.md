# GenAI Medical Chatbot

A **Retrieval-Augmented Generation (RAG)** medical assistant that answers clinical questions grounded in a real medical knowledge base — not hallucinated responses. Built with LangChain, Pinecone, Flask, and deployed on AWS EC2 via Docker and GitHub Actions CI/CD.

[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-RAG-green?logo=chainlink)](https://langchain.com)
[![Pinecone](https://img.shields.io/badge/Pinecone-Vector_DB-purple)](https://pinecone.io)
[![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20ECR-orange?logo=amazonaws)](https://aws.amazon.com)
[![Flask](https://img.shields.io/badge/Flask-Web_UI-black?logo=flask)](https://flask.palletsprojects.com)

---

## Overview

Standard LLMs hallucinate on domain-specific medical questions. This system replaces prompt-only responses with a RAG pipeline: medical PDF documents are chunked, embedded, and stored in Pinecone. At query time, relevant chunks are retrieved and injected into the LLM context — grounding every answer in the actual knowledge base.

**Key safeguards built in:**
- Emergency detection: automatically routes suicidal/crisis queries to appropriate resources
- Medical focus enforcement: redirects off-topic questions back to medical domain
- "No match" fallback: when no relevant context is found, directs to a healthcare professional rather than guessing

---

## Architecture

```
Medical PDF Documents
        │
        ▼
┌─────────────────────┐
│   store_index.py    │  ← Load PDFs → chunk → embed → store in Pinecone
└─────────────────────┘
        │
        ▼  (at query time)
┌──────────────────────────────────────────────┐
│                 RAG Pipeline                 │
│                                              │
│  User Query                                  │
│      │                                       │
│      ▼                                       │
│  Pinecone Retrieval  ← semantic search       │
│      │   (top-3 chunks)                      │
│      ▼                                       │
│  LLM (Gemma 3 27B via OpenRouter)            │
│      │   + retrieved context + chat history  │
│      ▼                                       │
│  Grounded Medical Response                   │
└──────────────────────────────────────────────┘
        │
        ▼
Flask Web UI  →  AWS EC2 (Docker + GitHub Actions CI/CD)
```

---

## Features

- **RAG-based Medical Assistant** — answers grounded in uploaded medical documents, not model weights
- **Conversation Memory** — maintains chat history during the session via Redis (filesystem fallback)
- **Emergency Response** — detects and routes crisis/suicidal queries to appropriate resources
- **Medical Focus** — automatically redirects non-medical questions
- **Semantic Search** — Pinecone vector DB with cosine similarity retrieval
- **Performance Monitoring** — real-time P50/P95 latency metrics for end-to-end and retrieval latency
- **Debug Tooling** — session inspection endpoint for development
- **Responsive Web UI** — Flask + Bootstrap chat interface
- **Production-Ready Deployment** — Docker + AWS ECR + EC2 + GitHub Actions CI/CD

---

## Tech Stack

| Component | Technology |
|---|---|
| RAG orchestration | LangChain |
| Vector database | Pinecone (`all-MiniLM-L6-v2`, 384-dim, cosine) |
| LLM | Google Gemma 3 27B via OpenRouter API |
| Embeddings | HuggingFace `sentence-transformers/all-MiniLM-L6-v2` |
| Web framework | Flask + Bootstrap |
| Session storage | Redis (filesystem fallback) |
| Containerization | Docker |
| Cloud hosting | AWS EC2 + ECR |
| CI/CD | GitHub Actions |
| Language | Python 3.8+ |

---

## Quick Start

### STEP 01 — Clone the Repository

```bash
git clone https://github.com/panditpooja/genAI-medical-chatbot-with-LLM-LangChain-PineconeVectDb-Flask-AWS.git
cd genAI-medical-chatbot-with-LLM-LangChain-PineconeVectDb-Flask-AWS
```

### STEP 02 — Create a Virtual Environment

**Option A: Python venv (Recommended)**
```bash
python -m venv .venv

# Activate — Windows:
.venv\Scripts\activate

# Activate — Linux/Mac:
source .venv/bin/activate
```

**Option B: Conda**
```bash
conda create -n medical-chatbot python=3.10
conda activate medical-chatbot
```

### STEP 03 — Install Dependencies

```bash
pip install -r requirements.txt
```

### STEP 04 — Install and Start Redis

Redis is recommended for server-side session storage. The app falls back to filesystem sessions automatically if Redis is unavailable.

**Windows:**
```bash
# Option A — WSL (Recommended)
sudo apt-get update && sudo apt-get install redis-server
sudo service redis-server start
```

**Option B — Native Windows:**
- Download from https://github.com/microsoftarchive/redis/releases and run `redis-server.exe`
- Or install [Memurai](https://www.memurai.com/) (Redis-compatible for Windows)

```bash
# Option C — Docker
docker run -d -p 6379:6379 redis:alpine

# Option D — Skip for development: set USE_REDIS=false in .env
# The app will use filesystem sessions (single-user dev only)
```

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server && sudo systemctl start redis-server

# Mac (Homebrew)
brew install redis && brew services start redis
```

**Verify Redis:**
```bash
redis-cli ping   # Should return: PONG
```

### STEP 05 — Configure Environment Variables

Create a `.env` file in the project root:

```ini
# Required
PINECONE_API_KEY=your_pinecone_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional Redis (defaults shown)
USE_REDIS=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Optional — set for production
FLASK_SECRET_KEY=your_secret_key_here
```

### STEP 06 — Store Embeddings in Pinecone

Add your PDF files to the `data/` directory, then run:

```bash
python store_index.py
```

This loads PDFs → splits into chunks → generates embeddings → stores in your Pinecone index.

### STEP 07 — Run the Application

```bash
python app.py
```

The app starts at `http://0.0.0.0:8080`

> **Note:** Using `flask run` without `--host 0.0.0.0 --port 8080` defaults to `127.0.0.1:5000` and ignores the settings in `app.py`.

### STEP 08 — Access the Chatbot

Open `http://localhost:8080` in your browser.

> **Accessing from another device on the same network?** Use `http://<your-ip-address>:8080` instead of `localhost`.

---

## Project Structure

```
genAI/
├── app.py                      # Main Flask application
├── store_index.py              # Embed documents and store in Pinecone
├── requirements.txt
├── setup.py
├── Dockerfile
├── .env                        # Create this (not committed)
├── data/
│   └── Medical_book.pdf        # Place medical PDFs here
├── src/
│   ├── __init__.py
│   ├── helper.py               # PDF loading, text splitting, embeddings
│   ├── prompt.py               # System prompts
│   ├── metrics.py              # Latency metrics (P50/P95)
│   └── retriever_wrapper.py    # Retriever with latency tracking
├── templates/
│   └── chat.html               # Chat UI
└── static/
    └── style.css
```

---

## Performance Monitoring

The application tracks two latency metrics in real time:

| Metric | Description |
|---|---|
| End-to-End Response Latency | Total time from request to response (seconds) |
| Retrieval Latency | Time to retrieve chunks from Pinecone (milliseconds) |

**Endpoints:**
- `http://localhost:8080/metrics` — JSON with P50/P95 percentiles
- `http://localhost:8080/metrics/summary` — Human-readable summary
- `http://localhost:8080/debug/session` — Inspect current session data

**Sample output:**
```
=== Latency Metrics ===
Total Samples: 150 | Retrieval Samples: 145

End-to-End Response Latency (seconds):
  P50: 2.345s  |  P95: 4.567s

Retrieval Latency (milliseconds):
  P50: 123.45ms  |  P95: 234.56ms
```

> **Note:** In multi-worker deployments (gunicorn), metrics are tracked per worker process.

---

## AWS CI/CD Deployment

### 1. Create IAM User

Create an IAM user with:
- `AmazonEC2ContainerRegistryFullAccess`
- `AmazonEC2FullAccess`

### 2. Create ECR Repository

Navigate to ECR in the AWS Console and create a repository (e.g., `medicalbot`). Save the URI:
```
<your-account-id>.dkr.ecr.<your-region>.amazonaws.com/medicalbot
```

### 3. Launch EC2 Instance

- Ubuntu recommended
- Security group: open ports 22 (SSH), 80 (HTTP), 8080 (Flask)
- Save your key pair

### 4. Install Docker on EC2

```bash
sudo apt-get update -y && sudo apt-get upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
newgrp docker
```

### 5. Configure EC2 as GitHub Self-Hosted Runner

Go to **GitHub repo → Settings → Actions → Runners → New self-hosted runner** and follow the Linux instructions on your EC2 instance.

### 6. Add GitHub Secrets

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `AWS_DEFAULT_REGION` | e.g. `us-east-1` |
| `ECR_REPO` | ECR repository URI |
| `PINECONE_API_KEY` | Pinecone API key |
| `OPENROUTER_API_KEY` | OpenRouter API key |

The GitHub Actions workflow (`.github/workflows/deploy.yml`) builds the Docker image → pushes to ECR → SSH into EC2 → pulls and runs the updated container.

---

## Configuration Reference

**Pinecone Index:**
- Index name: `medical-chatbot`
- Dimension: 384 (for `all-MiniLM-L6-v2`)
- Metric: Cosine similarity

**Model:**
- LLM: Google Gemma 3 27B via OpenRouter
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- Temperature: 0 (consistent responses)
- Retrieval: top-3 most similar chunks

**Metrics Storage:**
- Max samples: 10,000 per metric type (configurable in `src/metrics.py`)
- Storage: in-memory (thread-safe)
- Persistence: metrics reset on server restart
- Multi-worker: each gunicorn worker tracks its own metrics (see `METRICS_LIMITATIONS.md`)

**Session Management:**
- Sessions expire after 1 hour of inactivity
- Redis = production recommended; filesystem = auto-fallback for dev

---

## Usage Notes

1. **Medical questions** — ask anything covered by the documents in `data/`
2. **Non-medical questions** — chatbot politely redirects
3. **Unknown context** — responds with "consult a healthcare professional" rather than guessing
4. **Emergency detection** — crisis/suicidal queries trigger immediate resource routing
5. **Session context** — chat history is maintained within the session

> **Disclaimer:** This chatbot is for informational purposes only and does not replace professional medical advice. Always consult a licensed healthcare professional for medical decisions.

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the [Apache License 2.0](LICENSE).

## Acknowledgments

- [LangChain](https://langchain.com) community for the excellent RAG framework
- [Pinecone](https://pinecone.io) for vector database services
- [OpenRouter](https://openrouter.ai) for LLM API access
- [HuggingFace](https://huggingface.co) for sentence transformer embeddings

---

## Author

**Pooja Diwakar Pandit**  
M.S. Information Science (Machine Learning) · GPA 4.0 · University of Arizona  
IEEE First Author · Distinguished Graduate Scholar

[![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github)](https://github.com/panditpooja)
[![LinkedIn](https://img.shields.io/badge/-LinkedIn-0A66C2?style=flat&logo=linkedin)](https://www.linkedin.com/in/pooja-pandit-177978135/)
[![Portfolio](https://img.shields.io/badge/-Portfolio-4CAF50?style=flat&logo=firefox)](https://poojapandit.pythonanywhere.com)
