import os
import re
import time
import redis

from flask import Flask, render_template, request, session, jsonify
from flask_session import Session
from dotenv import load_dotenv

from src.helper import download_hugging_face_embeddings
from src.prompt import system_prompt
from src.metrics import metrics_tracker
from src.retriever_wrapper import TimedRetriever

from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

load_dotenv() #Load the environment variables from the .env file

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(24).hex()

# Configure Redis for server-side sessions
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Redis connection configuration
redis_config = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "db": REDIS_DB,
    "decode_responses": False,
    "socket_connect_timeout": 5,  # 5 second timeout
    "socket_timeout": 5,
    "retry_on_timeout": True
}
if REDIS_PASSWORD:
    redis_config["password"] = REDIS_PASSWORD

# Create Redis connection for Flask-Session
# Try to connect to Redis, but fall back to filesystem sessions for development
USE_REDIS = os.getenv("USE_REDIS", "true").lower() == "true"
redis_available = False
redis_client = None

if USE_REDIS:
    try:
        redis_client = redis.Redis(**redis_config)
        # Test connection
        redis_client.ping()
        redis_available = True
        print("✓ Connected to Redis - using Redis-based sessions")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"⚠ Warning: Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT}")
        print(f"  Error: {str(e)}")
        print(f"  Falling back to filesystem sessions for development")
        print(f"  To use Redis: Install Redis and start it, or set USE_REDIS=false in .env")
        redis_available = False
        redis_client = None

# Configure Flask-Session
# Each user gets a unique session ID, and their chat history is stored separately
# This ensures thread-safety: User 1's session is completely isolated from User 2's session
if redis_available:
    # Use Redis for server-side sessions (production-ready)
    app.config["SESSION_TYPE"] = "redis"
    app.config["SESSION_REDIS"] = redis_client
    app.config["SESSION_KEY_PREFIX"] = "medical_chatbot:session:"  # Prefix for Redis keys (unique per session)
else:
    # Use filesystem sessions as fallback (development only)
    # Note: Filesystem sessions work for single-server deployment but won't scale across multiple servers
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = os.path.join(os.getcwd(), "flask_session")  # Directory to store session files
    app.config["SESSION_FILE_THRESHOLD"] = 500  # Maximum number of sessions stored

# Common session settings
app.config["SESSION_PERMANENT"] = False  # Sessions expire when browser closes
app.config["SESSION_USE_SIGNER"] = True  # Sign session cookie for security
app.config["SESSION_COOKIE_SECURE"] = False  # Set to True in production with HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF protection
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour


# Initialize Flask-Session
# This ensures each user's session is stored in Redis/filesystem with a unique key
# Thread-safety is guaranteed: Flask-Session uses the session ID from the cookie
# to retrieve the correct session data for each request
session_interface = Session(app)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Validate API keys are set
if not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY is not set in environment variables. "
        "Please create a .env file with your OpenRouter API key. "
        "See README.md for setup instructions."
    )
if not PINECONE_API_KEY:
    raise ValueError(
        "PINECONE_API_KEY is not set in environment variables. "
        "Please create a .env file with your Pinecone API key. "
        "See README.md for setup instructions."
    )

embeddings = download_hugging_face_embeddings()

index_name = "medical-chatbot"

# Connect to existing Vector DB
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)

base_retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k":3})
# Wrap retriever to track retrieval latency
retriever = TimedRetriever(base_retriever, metrics_tracker)

# Defining the model
llm = ChatOpenAI(
    model="google/gemma-3-27b-it:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    temperature=0
)

# Prompt template with chat history support
prompt_template = (
    system_prompt +
    "\n\n=== PREVIOUS CONVERSATION HISTORY ===\n{chat_history}\n=== END OF CONVERSATION HISTORY ===\n\n"
    "CRITICAL INSTRUCTIONS:"
    "\n- If the conversation history above shows 'No previous conversation', this is the FIRST message."
    "\n- If the conversation history above shows ANY Human/Assistant messages, this is NOT the first message."
    "\n- If this is NOT the first message, answer the question directly. DO NOT greet. DO NOT say 'how can I help you'. DO NOT use names."
    "\n- Start your response immediately with the answer to the medical question.\n\n"
    "Current question: {input}"
)

prompt = ChatPromptTemplate.from_template(prompt_template)

# Create the question-answer chain with LLM
question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

@app.route("/")
def index():
    # Clear chat history on page load/refresh
    if "chat_history" in session:
        session.pop("chat_history", None)
        session.modified = True
    return render_template('chat.html')

@app.route("/metrics")
def metrics():
    """
    Endpoint to view latency metrics.
    
    NOTE: In multi-worker deployments (e.g., gunicorn), this shows metrics
    only for the worker process that handles this request. Metrics are NOT
    aggregated across all workers.
    """
    metrics_data = metrics_tracker.get_metrics()
    return jsonify(metrics_data)

@app.route("/metrics/summary")
def metrics_summary():
    """Endpoint to view formatted metrics summary."""
    summary = metrics_tracker.get_summary()
    return f"<pre>{summary}</pre>"

@app.route("/debug/session")
def debug_session():
    """Debug endpoint to inspect session data."""
    return jsonify({
        "session_keys": list(session.keys()),
        "chat_history_len": len(session.get("chat_history", [])),
        "chat_history_preview": session.get("chat_history", [])[-6:],  # last 3 turns
    })

def check_dangerous_keywords(message):
    """Check if message contains dangerous/suicidal keywords and return appropriate response"""
    dangerous_keywords = [
        'suicidal', 'suicide', 'kill myself', 'end my life', 'want to die',
        'harm myself', 'self harm', 'hurting myself', 'thoughts of suicide',
        'thinking about suicide', 'considering suicide', 'don\'t want to live', 
        'don\'t want to be here', 'don\'t want to be alive', "ending my life", 
        "end it all", "kill me", "take my life", "i can't go on", 
        "i want to disappear", "no reason to live"
    ]
    
    message_lower = message.lower()
    for keyword in dangerous_keywords:
        if keyword in message_lower:
            return (
                "This is an emergency situation that requires immediate help and support. "
                "Please call 988 (the Suicide and Crisis Lifeline) right now - they have caring counselors "
                "available 24/7 who want to listen and help. Also, please tell your primary care doctor about "
                "these feelings as soon as possible - they can connect you with mental health professionals. "
                "You don't have to go through this alone - caring help is available right now.<br><br>"
                "Remember: You can reach the Suicide and Crisis Lifeline by:<br>"
                "• Calling or texting 988<br>"
                "• Using online chat at 988lifeline.org<br>"
                "• For Veterans, press 1 after dialing 988"
            )
    return None

@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    print(f"User input: {msg}")
    
    # Check for dangerous/suicidal keywords first
    emergency_response = check_dangerous_keywords(msg)
    if emergency_response:
        print(f"Emergency response triggered")
        # Clean up whitespace for emergency response too
        emergency_response = emergency_response.strip()
        emergency_response = re.sub(r'\n{3,}', '\n\n', emergency_response)
        emergency_response = re.sub(r'^\n+|\n+$', '', emergency_response)
        # Update chat history
        if "chat_history" not in session:
            session["chat_history"] = []
        session["chat_history"].append(("human", msg))
        session["chat_history"].append(("ai", emergency_response))
        session.modified = True
        return emergency_response
    
    # Initialize chat history in session if not exists
    if "chat_history" not in session:
        session["chat_history"] = []
    
    # Format chat history as a string
    chat_history_str = ""
    if session["chat_history"]:
        history_lines = []
        for role, content in session["chat_history"]:
            if role == "human":
                history_lines.append(f"Human: {content}")
            elif role == "ai":
                history_lines.append(f"Assistant: {content}")
        chat_history_str = "\n".join(history_lines)
    else:
        chat_history_str = "No previous conversation."
    
    # Check if this is a simple gratitude/acknowledgment message
    # If so, we'll skip RAG retrieval and respond conversationally
    msg_lower = msg.lower()
    gratitude_keywords = ['thanks', 'thank you', 'appreciate', 'grateful', 'helpful']
    is_gratitude = any(keyword in msg_lower for keyword in gratitude_keywords) and len(msg.split()) < 15
    
    # Start timing for end-to-end latency
    total_start_time = time.perf_counter()
    
    if is_gratitude and session["chat_history"]:
        # For gratitude messages, respond conversationally without RAG
        # Use a simple LLM call with just the conversation history
        gratitude_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a compassionate medical assistant. The user just thanked you. "
             "Respond warmly and briefly (1-2 sentences). Reference the previous conversation if relevant. "
             "Be conversational and empathetic."),
            ("human", "Previous conversation:\n{chat_history}\n\nUser's message: {input}")
        ])
        
        gratitude_chain = gratitude_prompt | llm
        response = gratitude_chain.invoke({
            "input": msg,
            "chat_history": chat_history_str
        })
        answer = response.content if hasattr(response, 'content') else str(response)
    else:
        # Invoke RAG chain with chat history for medical questions
        response = rag_chain.invoke({
            "input": msg,
            "chat_history": chat_history_str
        })
        answer = response["answer"]
    
    # Calculate and record total end-to-end latency
    total_latency_seconds = time.perf_counter() - total_start_time
    metrics_tracker.record_total_latency(total_latency_seconds)
    
    # Clean up excessive whitespace: strip leading/trailing and normalize multiple newlines
    answer = answer.strip()  # Remove leading/trailing whitespace
    answer = re.sub(r'\n{3,}', '\n\n', answer)  # Replace 3+ newlines with just 2
    answer = re.sub(r'^\n+|\n+$', '', answer)  # Remove leading/trailing newlines again after normalization
    
    print(f"Response: {answer}")
    
    # Update chat history in session (store as tuples for JSON serialization)
    session["chat_history"].append(("human", msg))
    session["chat_history"].append(("ai", answer))
    
    # Keep only last 10 exchanges to avoid session size issues
    if len(session["chat_history"]) > 20:  # 10 exchanges = 20 messages
        session["chat_history"] = session["chat_history"][-20:]
    
    session.modified = True  # Mark session as modified
    
    return str(answer)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)