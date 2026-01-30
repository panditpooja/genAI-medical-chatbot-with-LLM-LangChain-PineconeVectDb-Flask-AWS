# GenAI Medical Chatbot (LangChain + Pinecone + Flask + AWS)

A comprehensive medical chatbot application built with LangChain, Pinecone Vector Database, Flask, and deployed on AWS. This chatbot uses Retrieval Augmented Generation (RAG) to provide accurate medical information based on a knowledge base of medical documents.

## Features

- 🤖 **RAG-based Medical Assistant**: Answers medical questions using context from uploaded medical documents
- 💬 **Conversation Memory**: Maintains conversation history during the session
- 🚨 **Emergency Response**: Automatically detects and responds to suicidal/dangerous queries with appropriate resources
- 🏥 **Medical Focus**: Automatically redirects non-medical questions to keep conversations on medical topics
- 🔍 **Semantic Search**: Uses Pinecone vector database for efficient document retrieval
- 📊 **Performance Monitoring**: Real-time latency metrics tracking with P50/P95 percentiles
- 🐛 **Debug Tools**: Session inspection endpoint for debugging
- 💻 **Web Interface**: Clean, responsive chat interface built with Flask and Bootstrap
- ☁️ **AWS Deployment**: Ready for deployment on AWS EC2 with Docker and GitHub Actions CI/CD

## Tech Stack

- **Python** - Core programming language
- **LangChain** - Framework for building LLM applications
- **Flask** - Web framework for the chat interface
- **OpenRouter API** - LLM provider (using Google Gemma 3 27B model)
- **Pinecone** - Vector database for embeddings storage
- **HuggingFace** - Sentence transformers for embeddings
- **Docker** - Containerization for deployment
- **AWS EC2** - Cloud hosting
- **GitHub Actions** - CI/CD pipeline

## Prerequisites

- Python 3.8 or higher
- Anaconda or Python virtual environment
- Redis server (for session storage)
- Pinecone API key
- OpenRouter API key (for LLM access)
- AWS account (for deployment)

## How to Run

### STEP 01 - Clone the Repository

```bash
git clone https://github.com/panditpooja/genAI-medical-chatbot-with-LLM-LangChain-PineconeVectDb-Flask-AWS.git
cd genAI-medical-chatbot-with-LLM-LangChain-PineconeVectDb-Flask-AWS
```

### STEP 02 - Create a Virtual Environment

**Option A: Using Python venv (Recommended)**

```bash
python -m venv .venv
```

**Activate the virtual environment:**

- **Windows:**
  ```bash
  .venv\Scripts\activate
  ```

- **Linux/Mac:**
  ```bash
  source .venv/bin/activate
  ```

**Option B: Using Conda**

```bash
conda create -n medical-chatbot python=3.10
conda activate medical-chatbot
```

### STEP 03 - Install Dependencies

```bash
pip install -r requirements.txt
```

### STEP 04 - Install and Start Redis

**Redis is recommended for server-side session storage (chat history).**

**Note:** The application will automatically fall back to filesystem sessions if Redis is not available. However, Redis is recommended for production use.

**Windows:**
1. **Option A (Recommended - WSL):**
   - Install WSL (Windows Subsystem for Linux)
   - In WSL terminal: `sudo apt-get update && sudo apt-get install redis-server`
   - Start Redis: `sudo service redis-server start` or `redis-server`

2. **Option B (Native Windows):**
   - Download Redis from https://github.com/microsoftarchive/redis/releases
   - Extract and run `redis-server.exe` from the extracted folder
   - Or install via Memurai (Redis-compatible): https://www.memurai.com/

3. **Option C (Docker):**
   - Install Docker Desktop
   - Run: `docker run -d -p 6379:6379 redis:alpine`

4. **Option D (Skip Redis for Development):**
   - Set `USE_REDIS=false` in your `.env` file
   - The app will use filesystem sessions (works for single-user development)

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# Mac (using Homebrew)
brew install redis
brew services start redis

# Or run directly
redis-server
```

**Verify Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

### STEP 05 - Configure Environment Variables

Create a `.env` file in the root directory and add your API credentials:

```ini
PINECONE_API_KEY=your_pinecone_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

**Optional Redis configuration (defaults shown):**
```ini
USE_REDIS=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

**Note:** If Redis is not available, the application will automatically fall back to filesystem sessions for development. For production, Redis is recommended for better performance and multi-server support.

**Note:** For production, you can also set `FLASK_SECRET_KEY` in the `.env` file:
```ini
FLASK_SECRET_KEY=your_secret_key_here
```

### STEP 06 - Store Embeddings to Pinecone

Before running the application, you need to process your medical documents and store them in Pinecone:

```bash
python store_index.py
```

This script will:
- Load PDF files from the `data/` directory
- Split them into chunks
- Generate embeddings using HuggingFace models
- Store them in your Pinecone index

**Note:** Make sure you have PDF files in the `data/` directory before running this command.

### STEP 07 - Run the Application

**Option A: Using `python app.py` (Recommended)**

```bash
python app.py
```

The application will start on `http://0.0.0.0:8080`

**Option B: Using `flask run`**

If you prefer using Flask's CLI, you need to specify the host and port:

```bash
flask --app app.py run --host 0.0.0.0 --port 8080
```

**Note:** If you use `flask run` without specifying `--host` and `--port`, Flask will default to `http://127.0.0.1:5000`, which ignores the settings in your `if __name__ == '__main__'` block.

### STEP 08 - Access the Chatbot

Open your browser and navigate to:

```
http://localhost:8080
```

**Note:** If you're accessing from another device on the same network, use `http://<your-ip-address>:8080` instead of `localhost`.

You should see the medical chatbot interface. Start chatting!

## Project Structure

```
genAI/
├── app.py                 # Main Flask application
├── store_index.py         # Script to store embeddings in Pinecone
├── requirements.txt       # Python dependencies
├── setup.py              # Package setup file
├── Dockerfile             # Docker configuration for deployment
├── .env                  # Environment variables (create this)
├── data/                 # Medical PDF documents directory
│   └── Medical_book.pdf
├── src/
│   ├── __init__.py
│   ├── helper.py         # Utility functions (PDF loading, text splitting, embeddings)
│   ├── prompt.py         # System prompts for the chatbot
│   ├── metrics.py        # Latency metrics tracking module
│   └── retriever_wrapper.py  # Retriever wrapper for latency tracking
├── templates/
│   └── chat.html         # Chat interface template
└── static/
    └── style.css         # Custom styles
```

## Usage

1. **First Interaction**: The chatbot will greet you if you say hello or introduce yourself
2. **Medical Questions**: Ask any medical question based on the documents in your knowledge base
3. **Non-Medical Questions**: The chatbot will politely redirect non-medical questions and ask you to focus on medical topics
4. **Conversation Context**: The chatbot remembers the conversation during the session
5. **Emergency Detection**: If you mention suicidal thoughts, the chatbot will provide emergency resources
6. **Unknown Questions**: If the chatbot doesn't have information, it will suggest consulting healthcare professionals

## Performance Monitoring

The application tracks latency metrics to monitor performance:

### Metrics Tracked

- **End-to-End Response Latency**: Total time from request to response (in seconds)
- **Retrieval Latency**: Time to retrieve documents from Pinecone (in milliseconds)

### View Metrics

**Via Web Browser:**
- JSON format: `http://localhost:8080/metrics` - Returns JSON with P50/P95 percentiles
- Formatted summary: `http://localhost:8080/metrics/summary` - Human-readable format

**Debug Endpoint:**
- Session inspection: `http://localhost:8080/debug/session` - View current session data and chat history

### Metrics Output

The metrics include:
- **P50 (Median)**: 50th percentile - half of requests are faster, half are slower
- **P95**: 95th percentile - 95% of requests are faster than this value
- Sample counts for both metrics

**Example Output:**
```
=== Latency Metrics ===
Worker/Process ID: process-12345 (PID: 12345)
Total Samples: 150
Retrieval Samples: 145

End-to-End Response Latency (seconds):
  P50: 2.345s
  P95: 4.567s

Retrieval Latency (milliseconds):
  P50: 123.45ms
  P95: 234.56ms
```

**Note**: In multi-worker deployments (e.g., gunicorn with multiple workers), metrics are tracked per worker process. Each worker maintains its own metrics, so the `/metrics` endpoint will show metrics only for the worker that handles that request.

## AWS CI/CD Deployment with GitHub Actions

This section covers deploying the chatbot to AWS EC2 using Docker and GitHub Actions.

### 1. Login to AWS Console

Log in to your AWS account at https://console.aws.amazon.com

### 2. Create IAM User for Deployment

Create an IAM user with the following access:

**Required Access:**
- **EC2 Access**: For managing virtual machines
- **ECR Access**: Elastic Container Registry to store Docker images

**Description:**
The deployment process involves:
1. Building a Docker image of the source code
2. Pushing the Docker image to ECR
3. Launching an EC2 instance
4. Pulling the image from ECR in EC2
5. Running the Docker container in EC2

**Required Policies:**
- `AmazonEC2ContainerRegistryFullAccess`
- `AmazonEC2FullAccess`

### 3. Create ECR Repository

1. Navigate to ECR in AWS Console
2. Create a new repository (e.g., `medicalbot`)
3. Save the repository URI (e.g., `315865595366.dkr.ecr.us-east-1.amazonaws.com/medicalbot`)

### 4. Create EC2 Instance

1. Launch an EC2 instance (Ubuntu recommended)
2. Configure security groups to allow:
   - SSH (port 22)
   - HTTP (port 80)
   - Custom TCP (port 8080 for Flask app)
3. Save your key pair for SSH access

### 5. Install Docker in EC2

SSH into your EC2 instance and run:

```bash
# Optional: Update system
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Verify installation
docker --version
```

### 6. Configure EC2 as Self-Hosted Runner

1. Go to your GitHub repository
2. Navigate to **Settings > Actions > Runners**
3. Click **New self-hosted runner**
4. Select your operating system (Linux)
5. Follow the instructions to download and configure the runner on your EC2 instance
6. Run the provided commands one by one on your EC2 instance

### 7. Setup GitHub Secrets

In your GitHub repository, go to **Settings > Secrets and variables > Actions** and add the following secrets:

- `AWS_ACCESS_KEY_ID` - Your IAM user access key
- `AWS_SECRET_ACCESS_KEY` - Your IAM user secret key
- `AWS_DEFAULT_REGION` - Your AWS region (e.g., `us-east-1`)
- `ECR_REPO` - Your ECR repository URI
- `PINECONE_API_KEY` - Your Pinecone API key
- `OPENROUTER_API_KEY` - Your OpenRouter API key

### 8. GitHub Actions Workflow

Create a `.github/workflows/deploy.yml` file in your repository with your deployment workflow. The workflow should:

1. Build the Docker image
2. Push to ECR
3. SSH into EC2
4. Pull the latest image
5. Stop and remove old containers
6. Run the new container

## Configuration

### Pinecone Index

- **Index Name**: `medical-chatbot`
- **Dimension**: 384 (for `all-MiniLM-L6-v2` embeddings)
- **Metric**: Cosine similarity

### Model Configuration

- **LLM**: Google Gemma 3 27B (via OpenRouter)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`
- **Temperature**: 0 (for consistent responses)
- **Retrieval**: Top 3 most similar chunks

### Metrics Configuration

- **Max Samples**: 10,000 per metric type (configurable in `src/metrics.py`)
- **Storage**: In-memory (thread-safe)
- **Persistence**: Metrics reset on server restart
- **Multi-Worker**: Metrics tracked per worker process (see `METRICS_LIMITATIONS.md` for details)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## ✍️ Author

**Pooja Pandit**  
Master's in Information Science (Machine Learning)  
The University of Arizona

[![GitHub](https://img.shields.io/badge/GitHub-panditpooja-black?logo=github)](https://github.com/panditpooja)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-pooja--pandit-blue?logo=linkedin)](https://www.linkedin.com/in/pooja-pandit-177978135/)

## Acknowledgments

- LangChain community for the excellent framework
- Pinecone for vector database services
- OpenRouter for LLM API access
- HuggingFace for embeddings models

## Additional Information

### Session Management

The application uses server-side sessions for storing chat history:
- **Redis** (recommended): For production deployments with multiple servers
- **Filesystem** (fallback): Automatically used if Redis is unavailable (development mode)

Sessions are automatically managed and expire after 1 hour of inactivity.

### Debug Endpoints

- `/debug/session`: Inspect current session data, including chat history length and preview

## Support

For issues and questions, please open an issue on the GitHub repository.

---

**Note**: This chatbot is for informational purposes only and should not replace professional medical advice. Always consult with healthcare professionals for medical decisions.
