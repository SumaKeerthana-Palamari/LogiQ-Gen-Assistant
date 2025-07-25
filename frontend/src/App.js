import React, { useState, useEffect, useRef } from 'react';
import './App.css';

// IMPORTANT: Replace this with your actual Render backend URL
const API_BASE = process.env.REACT_APP_API_URL || 'https://logiq-gen-assistant-1.onrender.com/api';

// Generate UUID
const generateId = () => Math.random().toString(36).substr(2, 9);

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chatHistory, setChatHistory] = useState([]);
  const messagesEndRef = useRef(null);

  // Scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize session
  useEffect(() => {
    initializeSession();
  }, []);

  const initializeSession = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE}/chat/session/new`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) throw new Error('Failed to create session');

      const data = await response.json();
      setSessionId(data.session_id);
      setIsConnected(true);
      setError(null);

      // Add welcome message
      const welcomeMessage = {
        id: generateId(),
        content: "Hello! I'm the LogiQ Gen assistant. How can I help you today?",
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages([welcomeMessage]);

      // Add to chat history
      const newChat = {
        id: data.session_id,
        title: "New Chat",
        timestamp: new Date(),
        preview: "Hello! I'm the LogiQ Gen assistant..."
      };
      setChatHistory(prev => [newChat, ...prev]);

    } catch (err) {
      console.error('Failed to initialize session:', err);
      setError('Failed to connect to chatbot service');
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || isLoading) return;

    const userMessage = {
      id: generateId(),
      content: input.trim(),
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: userMessage.content,
          session_id: sessionId
        })
      });

      if (!response.ok) throw new Error('Failed to send message');

      const data = await response.json();
      
      const botMessage = {
        id: generateId(),
        content: data.message,
        sender: 'bot',
        timestamp: new Date(data.timestamp),
        confidence: data.confidence,
        suggestions: data.suggestions
      };

      setMessages(prev => [...prev, botMessage]);

      // Update chat history
      setChatHistory(prev => prev.map(chat => 
        chat.id === sessionId 
          ? { ...chat, preview: userMessage.content.substring(0, 50) + "...", timestamp: new Date() }
          : chat
      ));

    } catch (err) {
      console.error('Failed to send message:', err);
      const errorMessage = {
        id: generateId(),
        content: "I'm sorry, I'm having trouble responding right now. Please try again.",
        sender: 'bot',
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
      setError('Failed to send message');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = async () => {
    if (window.confirm('Clear chat history?')) {
      try {
        if (sessionId) {
          await fetch(`${API_BASE}/chat/session/${sessionId}`, {
            method: 'DELETE'
          });
        }
        await initializeSession();
      } catch (err) {
        console.error('Failed to clear chat:', err);
      }
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setInput(suggestion);
  };

  const formatTime = (date) => {
    return new Date(date).toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className="App">
      {/* Top Navbar */}
      <nav className="navbar">
        <div className="navbar-left">
          <button className="sidebar-toggle" onClick={toggleSidebar}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
          <div className="brand">
            <h1>LogiQ Gen</h1>
            <span>AI Assistant</span>
          </div>
        </div>
        <div className="navbar-right">
          <div className="connection-status">
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
            <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
          <button className="new-chat-btn" onClick={clearChat} disabled={isLoading}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path>
            </svg>
            New Chat
          </button>
        </div>
      </nav>

      <div className="app-content">
        {/* Sidebar */}
        <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
          <div className="sidebar-header">
            <h3>Chat History</h3>
          </div>
          
          <div className="sidebar-content">
            {chatHistory.length > 0 ? (
              chatHistory.map((chat) => (
                <div key={chat.id} className="chat-item">
                  <div className="chat-title">{chat.title}</div>
                  <div className="chat-preview">{chat.preview}</div>
                  <div className="chat-time">{formatTime(chat.timestamp)}</div>
                </div>
              ))
            ) : (
              <div className="empty-history">
                <p>No chat history yet</p>
              </div>
            )}
          </div>

          <div className="sidebar-footer">
            <div className="menu-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.71a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
              Settings
            </div>
            <div className="menu-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="1"></circle>
                <circle cx="12" cy="5" r="1"></circle>
                <circle cx="12" cy="19" r="1"></circle>
              </svg>
              Help & Support
            </div>
          </div>
        </aside>

        {/* Main Chat Area */}
        <main className="chat-main">
          {error && (
            <div className="error-banner">
              <span>⚠️ {error}</span>
              <button onClick={() => setError(null)}>✕</button>
            </div>
          )}

          <div className="chat-container">
            <div className="messages">
              {messages.map((message) => (
                <div key={message.id} className={`message ${message.sender}`}>
                  <div className={`message-bubble ${message.isError ? 'error' : ''}`}>
                    {message.content}
                    {message.confidence && (
                      <div className="confidence">
                        Confidence: {Math.round(message.confidence * 100)}%
                      </div>
                    )}
                  </div>
                  <div className="message-time">
                    {formatTime(message.timestamp)}
                  </div>
                  {message.suggestions && (
                    <div className="suggestions">
                      <span className="suggestions-label">Suggestions:</span>
                      {message.suggestions.map((suggestion, index) => (
                        <button
                          key={index}
                          className="suggestion-chip"
                          onClick={() => handleSuggestionClick(suggestion)}
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="message bot">
                  <div className="typing-indicator">
                    <div className="typing-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <span>Assistant is typing...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="input-area">
              <div className="input-container">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={isConnected ? "Type your message..." : "Connecting..."}
                  disabled={!isConnected || isLoading}
                  maxLength={1000}
                />
                <button 
                  onClick={sendMessage}
                  disabled={!input.trim() || !isConnected || isLoading}
                  className="send-btn"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22,2 15,22 11,13 2,9"></polygon>
                  </svg>
                </button>
              </div>
              <div className="input-footer">
                <span>{input.length}/1000</span>
                <span>Press Enter to send</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
