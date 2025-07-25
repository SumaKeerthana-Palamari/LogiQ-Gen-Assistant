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
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="LogiQ Gen Professional Chatbot", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001",
        "https://logi-q-gen-assistant-6fia.vercel.app",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Try to import OpenAI (optional)
try:
    from openai import OpenAI
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        openai_client = OpenAI(api_key=openai_api_key)
        logger.info("OpenAI client initialized successfully")
        ai_enabled = True
    else:
        openai_client = None
        ai_enabled = False
        logger.info("OpenAI API key not found, using enhanced fallback")
except ImportError:
    openai_client = None
    ai_enabled = False
    logger.info("OpenAI not installed, using enhanced fallback")
except Exception as e:
    openai_client = None
    ai_enabled = False
    logger.error(f"OpenAI initialization error: {e}")

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
    source: Optional[str] = None

# In-memory storage
class MemoryService:
    def __init__(self):
        self._sessions: Dict[str, Dict] = {}
        self._messages: Dict[str, List] = {}
        self._context: Dict[str, Dict] = {}
        self._lock = threading.Lock()

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

# Enhanced Chatbot service
class ChatbotService:
    def __init__(self):
        self.enhanced_intents = {
            "greeting": {
                "patterns": ["hello", "hi", "hey", "good morning", "good afternoon", "greetings", "start"],
                "responses": [
                    "Hello! I'm LogiQ Gen's AI assistant. I specialize in helping businesses with AI, machine learning, and digital transformation solutions. How can I help accelerate your technology journey today?",
                    "Hi there! Welcome to LogiQ Gen. I'm here to discuss how our cutting-edge AI and ML solutions can transform your business. What technology challenges are you facing?",
                    "Greetings! I'm LogiQ Gen's digital transformation expert. Whether you need AI development, cloud migration, or data analytics, I'm here to help. What brings you here today?"
                ]
            },
            "company_info": {
                "patterns": ["about logiq gen", "what is logiq gen", "company information", "tell me about", "who are you"],
                "responses": [
                    "LogiQ Gen is a leading technology innovator specializing in AI, machine learning, and digital transformation. We help businesses harness the power of cutting-edge technology to solve complex challenges, optimize operations, and drive sustainable growth.",
                    "At LogiQ Gen, we're passionate pioneers in the AI revolution. We transform businesses through intelligent automation, predictive analytics, machine learning implementations, and comprehensive digital strategies."
                ]
            },
            "services": {
                "patterns": ["services", "what services", "offerings", "products", "solutions", "help", "offer"],
                "responses": [
                    "LogiQ Gen offers comprehensive technology services: AI development, machine learning solutions, data analytics, cloud migration, custom software development, and digital transformation consulting. We build solutions that deliver real business value.",
                    "Our key services include custom AI model development, cloud infrastructure design, data analytics platforms, digital process automation, and strategic technology consulting. What specific challenge can we help you solve?"
                ]
            },
            "ai_ml": {
                "patterns": ["ai", "artificial intelligence", "machine learning", "ml", "ai development", "smart systems"],
                "responses": [
                    "Our AI and Machine Learning services include custom AI model development, natural language processing, computer vision, predictive analytics, and intelligent automation. We build AI that solves real business problems and delivers measurable ROI.",
                    "LogiQ Gen's AI expertise covers neural networks, deep learning, NLP, computer vision, recommendation engines, and intelligent process automation. What specific AI challenge can we help you solve?"
                ]
            },
            "pricing": {
                "patterns": ["price", "cost", "pricing", "how much", "budget", "rates", "quote"],
                "responses": [
                    "Our pricing is tailored to deliver maximum value for your specific needs and budget. We offer flexible engagement models including project-based pricing and retainer agreements. For a detailed quote, I'd love to connect you with our solutions team at sales@logiqgen.com.",
                    "Investment in LogiQ Gen services varies based on project complexity and desired outcomes. For a customized proposal that fits your budget and goals, our sales team can provide detailed estimates. What specific services are you considering?"
                ]
            },
            "contact": {
                "patterns": ["contact", "support", "sales", "team", "talk to", "reach"],
                "responses": [
                    "I'm here to help right now! For immediate assistance, continue chatting with me. For detailed project discussions, our expert sales team is available at sales@logiqgen.com. What type of support do you need?",
                    "You can reach our team at sales@logiqgen.com for project inquiries, or continue this conversation for instant answers. How can we best assist you today?"
                ]
            },
            "goodbye": {
                "patterns": ["bye", "goodbye", "see you", "farewell", "thanks", "thank you"],
                "responses": [
                    "Thank you for exploring LogiQ Gen's capabilities! I'm here whenever you need insights about AI, digital transformation, or technology solutions. Feel free to reach out to sales@logiqgen.com for detailed discussions. Have a fantastic day!",
                    "It's been great discussing how LogiQ Gen can accelerate your technology goals! Don't hesitate to return with any questions about AI, cloud solutions, or digital transformation. Until next time!"
                ]
            }
        }

    def find_intent(self, text: str):
        text_lower = text.lower()
        intent_scores = {}
        
        for intent_name, intent_data in self.enhanced_intents.items():
            score = 0
            for pattern in intent_data["patterns"]:
                if pattern in text_lower:
                    score += len(pattern.split()) * 2
                    for word in pattern.split():
                        if word in text_lower:
                            score += 1
            intent_scores[intent_name] = score
        
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            if intent_scores[best_intent] > 0:
                return best_intent
        return None

    async def get_openai_response(self, user_input: str, conversation_history: List[Dict]) -> Optional[Dict]:
        """Get response from OpenAI API if available"""
        if not openai_client:
            return None
            
        try:
            messages = [
                {"role": "system", "content": "You are a professional AI assistant for LogiQ Gen, a leading technology company specializing in AI, machine learning, and digital transformation services. Be helpful, professional, and focus on how LogiQ Gen can solve technology challenges."}
            ]
            
            for msg in conversation_history[-4:]:
                role = "user" if msg["sender"] == "user" else "assistant"
                messages.append({"role": role, "content": msg["content"]})
            
            messages.append({"role": "user", "content": user_input})
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            return {
                "message": ai_response,
                "confidence": 0.9,
                "suggestions": self.generate_suggestions("ai_response"),
                "source": "openai"
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None

    def generate_suggestions(self, context: str) -> List[str]:
        suggestions = [
            "Tell me about LogiQ Gen's AI services",
            "What digital transformation solutions do you offer?", 
            "How can AI help my business?",
            "What are your cloud migration services?",
            "How much do your services cost?",
            "Can I speak with your sales team?"
        ]
        return random.sample(suggestions, 3)

    async def generate_response(self, user_input: str, session_id: str) -> Dict:
        conversation_history = memory.get_recent_messages(session_id, limit=4)
        
        # Try OpenAI first if available
        if ai_enabled:
            openai_response = await self.get_openai_response(user_input, conversation_history)
            if openai_response:
                return openai_response
        
        # Use enhanced rule-based fallback
        intent = self.find_intent(user_input)
        
        if intent and intent in self.enhanced_intents:
            responses = self.enhanced_intents[intent]["responses"]
            response = random.choice(responses)
            confidence = 0.8
        else:
            response = "I'd be happy to help you learn more about LogiQ Gen's AI, machine learning, and digital transformation services. What specific technology challenges is your organization facing?"
            confidence = 0.6
        
        return {
            "message": response,
            "confidence": confidence,
            "suggestions": self.generate_suggestions(intent or "default"),
            "source": "enhanced_fallback"
        }

# Global instances
memory = MemoryService()
chatbot = ChatbotService()

# API Routes
@app.get("/")
async def root():
    return {"message": "LogiQ Gen AI Chatbot API is running", "ai_enabled": ai_enabled}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "LogiQ Gen AI Chatbot",
        "ai_enabled": ai_enabled,
        "openai_configured": openai_api_key is not None if 'openai_api_key' in globals() else False
    }

@app.post("/api/chat/session/new")
async def create_new_session():
    try:
        session_id = str(uuid.uuid4())
        memory.create_session(session_id)
        return {
            "session_id": session_id,
            "status": "created",
            "timestamp": datetime.now(),
            "ai_enabled": ai_enabled
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

@app.post("/api/chat/message", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    try:
        session_id = message.session_id
        user_input = message.content
        
        if not memory.get_session(session_id):
            memory.create_session(session_id)
        
        memory.add_message(session_id, user_input, "user")
        
        # Extract user name if mentioned
        name_match = re.search(r"(?:my name is|i'm|i am|call me)\s+([a-zA-Z]+)", user_input.lower())
        if name_match:
            memory.set_context(session_id, "user_name", name_match.group(1).title())
        
        response_data = await chatbot.generate_response(user_input, session_id)
        
        # Personalize if name is known
        user_name = memory.get_context(session_id, "user_name")
        if user_name and "Hello!" in response_data["message"]:
            response_data["message"] = response_data["message"].replace("Hello!", f"Hello {user_name}!")
        
        memory.add_message(session_id, response_data["message"], "bot")
        
        return ChatResponse(
            message=response_data["message"],
            session_id=session_id,
            timestamp=datetime.now(),
            confidence=response_data["confidence"],
            suggestions=response_data["suggestions"],
            source=response_data.get("source", "unknown")
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return ChatResponse(
            message="I apologize, but I'm experiencing some technical difficulties. Please try again in a moment, or contact our sales team at sales@logiqgen.com for immediate assistance.",
            session_id=message.session_id,
            timestamp=datetime.now(),
            confidence=0.0,
            source="error_fallback"
        )

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
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat history")

@app.delete("/api/chat/session/{session_id}")
async def delete_session(session_id: str):
    try:
        if not memory.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        memory._sessions.pop(session_id, None)
        memory._messages.pop(session_id, None)
        memory._context.pop(session_id, None)
        
        return {"message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")

@app.get("/api/chat/stats")
async def get_system_stats():
    try:
        active_sessions = len(memory._sessions)
        return {
            "active_sessions": active_sessions,
            "system_status": "healthy",
            "ai_enabled": ai_enabled,
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system statistics")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
