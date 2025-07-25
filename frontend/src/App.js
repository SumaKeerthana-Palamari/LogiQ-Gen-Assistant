import React, { useState, useEffect } from 'react';
import './App.css';

const generateId = () => '_' + Math.random().toString(36).substr(2, 9);

function App() {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);

  // 🌐 Replace with your actual Render backend URL
  const API_BASE = 'https://logiq-gen-assistant-1.onrender.com';

  useEffect(() => {
    initializeSession();
  }, []);

  const initializeSession = async () => {
    try {
      setIsLoading(true);

      const welcomeInput = "Hi";
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: welcomeInput })
      });

      if (!response.ok) throw new Error("Failed to connect to backend");

      const data = await response.json();
      const welcomeMessage = {
        id: generateId(),
        content: data.response,
        sender: 'bot',
        timestamp: new Date()
      };

      setSessionId(generateId()); // simulated session ID
      setIsConnected(true);
      setMessages([welcomeMessage]);
      setChatHistory([
        {
          id: Date.now(),
          title: "New Chat",
          timestamp: new Date(),
          preview: welcomeMessage.content.substring(0, 50) + "..."
        }
      ]);

    } catch (err) {
      console.error('Failed to initialize session:', err);
      setError('Failed to connect to chatbot service');
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!userInput.trim()) return;

    const newUserMessage = {
      id: generateId(),
      content: userInput,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setUserInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: userInput })
      });

      const data = await response.json();

      const botMessage = {
        id: generateId(),
        content: data.response,
        sender: 'bot',
        timestamp: new Date()
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      console.error('Error sending message:', err);
      setError('Failed to get response');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>LogiQGen AI Assistant</h1>
      </header>

      <main className="chat-container">
        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.sender}`}>
            <strong>{msg.sender === 'user' ? 'You' : 'Bot'}:</strong> {msg.content}
          </div>
        ))}
      </main>

      <footer className="input-bar">
        <input
          type="text"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Type your message..."
          disabled={!isConnected || isLoading}
        />
        <button onClick={sendMessage} disabled={!isConnected || isLoading}>
          {isLoading ? '...' : 'Send'}
        </button>
      </footer>

      {error && <div className="error">{error}</div>}
    </div>
  );
}

export default App;
