from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import re
import random
import threading
import uvicorn

# FastAPI app
app = FastAPI(title="LogiQ Gen Professional Chatbot", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class ChatMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)
    session_id: str = Field(..., min_length=1)

class ChatResponse(BaseModel):
    message: str
    session_id: str
    timestamp: datetime
    confidence: Optional[float] = None
    suggestions: Optional[List[str]] = None

# In-memory storage
class MemoryService:
    def __init__(self):
        self._sessions: Dict[str, Dict] = {}
        self._messages: Dict[str, List] = {}
        self._context: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._timeout = timedelta(minutes=30)

    def create_session(self, session_id: str):
        with self._lock:
            now = datetime.now()
            self._sessions[session_id] = {
                "created_at": now,
                "last_activity": now,
                "message_count": 0
            }
            self._messages[session_id] = []
            self._context[session_id] = {}

    def get_session(self, session_id: str):
        return self._sessions.get(session_id)

    def add_message(self, session_id: str, content: str, sender: str):
        with self._lock:
            if session_id not in self._sessions:
                self.create_session(session_id)
            
            message = {
                "content": content,
                "sender": sender,
                "timestamp": datetime.now()
            }
            self._messages[session_id].append(message)
            self._sessions[session_id]["message_count"] += 1
            self._sessions[session_id]["last_activity"] = datetime.now()

    def get_recent_messages(self, session_id: str, limit: int = 5):
        return self._messages.get(session_id, [])[-limit:]

    def set_context(self, session_id: str, key: str, value: Any):
        if session_id not in self._context:
            self._context[session_id] = {}
        self._context[session_id][key] = value

    def get_context(self, session_id: str, key: str = None):
        if session_id not in self._context:
            return None if key else {}
        if key:
            return self._context[session_id].get(key)
        return self._context[session_id]

# Chatbot service
class ChatbotService:
    def __init__(self):
        self.intents = {
            "greeting": {
                "patterns": ["hello", "hi", "hey", "good morning", "good afternoon", "greetings"],
                "responses": [
                    "Hello! I'm the LogiQ Gen assistant. How can I help you today?",
                    "Hi there! Welcome to LogiQ Gen. What can I do for you?",
                    "Greetings! I'm here to assist you with any questions about LogiQ Gen."
                ]
            },
            "company_info": {
                "patterns": ["about logiq gen", "what is logiq gen", "company information", "tell me about the company"],
                "responses": [
                    "LogiQ Gen is a leading technology company focused on delivering innovative solutions. We specialize in AI, machine learning, and digital transformation services.",
                    "At LogiQ Gen, we're passionate about leveraging cutting-edge technology to solve complex business challenges and drive digital innovation."
                ]
            },
            "services": {
                "patterns": ["services", "what services", "offerings", "products", "solutions"],
                "responses": [
                    "LogiQ Gen offers AI development, machine learning solutions, data analytics, cloud services, and digital transformation consulting.",
                    "Our key services include custom software development, AI/ML implementation, cloud migration, and digital strategy consulting."
                ]
            },
            "support": {
                "patterns": ["help", "support", "assistance", "problem", "contact"],
                "responses": [
                    "I'm here to help! Can you please describe the specific issue or question you have?",
                    "Our support team is ready to assist you. What kind of help do you need today?"
                ]
            },
            "pricing": {
                "patterns": ["pricing", "cost", "price", "how much", "rates", "quote"],
                "responses": [
                    "Our pricing varies based on project scope and requirements. I'd be happy to connect you with our sales team for a detailed quote.",
                    "For pricing information, please contact our sales team at sales@logiqgen.com for a customized quote."
                ]
            },
            "goodbye": {
                "patterns": ["bye", "goodbye", "see you later", "farewell"],
                "responses": [
                    "Thank you for chatting with LogiQ Gen! Have a great day!",
                    "Goodbye! Feel free to reach out anytime you need assistance."
                ]
            }
        }

    def find_intent(self, text: str):
        text_lower = text.lower()
        best_intent = None
        best_score = 0
        
        for intent_name, intent_data in self.intents.items():
            score = 0
            for pattern in intent_data["patterns"]:
                if pattern in text_lower:
                    score += len(pattern.split())
            
            if score > best_score:
                best_score = score
                best_intent = intent_name
        
        return best_intent if best_score > 0 else None

    def generate_response(self, intent: str, session_id: str):
        if intent and intent in self.intents:
            responses = self.intents[intent]["responses"]
            response = random.choice(responses)
            confidence = 0.8
            suggestions = self.get_suggestions(intent)
        else:
            fallback_responses = [
                "I'm not sure I understand that completely. Could you please rephrase your question?",
                "That's an interesting question! Could you provide a bit more detail so I can help you better?",
                "I'd be happy to help! Can you tell me more about what you're looking for?"
            ]
            response = random.choice(fallback_responses)
            confidence = 0.3
            suggestions = ["Tell me about Logiqgen", "What services do you offer?", "I need support"]
        
        return response, confidence, suggestions

    def get_suggestions(self, intent: str):
        suggestions_map = {
            "greeting": ["Tell me about LogiQ Gen", "What services do you offer?", "I need support"],
            "company_info": ["What services do you provide?", "How can I contact you?", "Pricing information"],
            "services": ["How much does it cost?", "Can I get a quote?", "Contact sales team"],
            "support": ["Technical support", "Sales inquiry", "General questions"],
            "pricing": ["Contact sales team", "Service details", "Custom quote"]
        }
        return suggestions_map.get(intent, ["Tell me about LogiQ Gen", "What services do you offer?"])

# Global instances
memory = MemoryService()
chatbot = ChatbotService()

# API Routes
@app.get("/")
async def root():
    return {"message": "LogiQ Gen Chatbot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "LogiQ Gen Chatbot"}

@app.post("/api/chat/session/new")
async def create_new_session():
    try:
        session_id = str(uuid.uuid4())
        memory.create_session(session_id)
        return {
            "session_id": session_id,
            "status": "created",
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create session")

@app.post("/api/chat/message", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    try:
        session_id = message.session_id
        user_input = message.content
        
        # Ensure session exists
        if not memory.get_session(session_id):
            memory.create_session(session_id)
        
        # Store user message
        memory.add_message(session_id, user_input, "user")
        
        # Extract user name if mentioned
        name_match = re.search(r"(?:my name is|i'm|i am|call me)\s+([a-zA-Z]+)", user_input.lower())
        if name_match:
            memory.set_context(session_id, "user_name", name_match.group(1).title())
        
        # Find intent and generate response
        intent = chatbot.find_intent(user_input)
        response_text, confidence, suggestions = chatbot.generate_response(intent, session_id)
        
        # Personalize if name is known
        user_name = memory.get_context(session_id, "user_name")
        if user_name and "Hello!" in response_text:
            response_text = response_text.replace("Hello!", f"Hello {user_name}!")
        
        # Store bot message
        memory.add_message(session_id, response_text, "bot")
        
        return ChatResponse(
            message=response_text,
            session_id=session_id,
            timestamp=datetime.now(),
            confidence=confidence,
            suggestions=suggestions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process message")

@app.get("/api/chat/session/{session_id}/history")
async def get_chat_history(session_id: str):
    try:
        if not memory.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = memory._messages.get(session_id, [])
        return {
            "session_id": session_id,
            "messages": messages,
            "total_messages": len(messages)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get chat history")

@app.delete("/api/chat/session/{session_id}")
async def delete_session(session_id: str):
    try:
        if not memory.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Clean up session data
        memory._sessions.pop(session_id, None)
        memory._messages.pop(session_id, None)
        memory._context.pop(session_id, None)
        
        return {"message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete session")

@app.get("/api/chat/stats")
async def get_system_stats():
    try:
        active_sessions = len(memory._sessions)
        return {
            "active_sessions": active_sessions,
            "system_status": "healthy",
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get system statistics")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)