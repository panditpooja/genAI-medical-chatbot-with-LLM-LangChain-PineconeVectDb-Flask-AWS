from flask import Flask, render_template, jsonify, request, session
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import *
import os
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

embeddings = download_hugging_face_embeddings()

index_name = "medical-chatbot" 

# Connect to existing Vector DB
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)

retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k":3})

# Defining the model
llm = ChatOpenAI(
    model="google/gemma-3-27b-it:free",  
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    temperature = 0
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

def check_dangerous_keywords(message):
    """Check if message contains dangerous/suicidal keywords and return appropriate response"""
    dangerous_keywords = [
        'suicidal', 'suicide', 'kill myself', 'end my life', 'want to die',
        'harm myself', 'self harm', 'hurting myself', 'thoughts of suicide',
        'thinking about suicide', 'considering suicide'
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
    app.run(host="0.0.0.0", port= 8080, debug= True)