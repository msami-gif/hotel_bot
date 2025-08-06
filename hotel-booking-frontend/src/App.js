// src/App.js
import React, { useState } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: '👋 Welcome to Hotel Bot! How can I help you today?' }
  ]);
  const [input, setInput] = useState('');

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);

    // Call your backend API
    try {
      const res = await fetch('http://127.0.0.1:8000/book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      });

      const data = await res.json();

      const hotelList = data.results
                        .split('Hotel:')
                        .slice(1)  // Skip the empty string before first 'Hotel:'
                        .map(h => `• Hotel: ${h.trim()}`)
                        .join('\n\n');

      const text = `${data.summary}\n\n${hotelList}`;

      const botMessage = { sender: 'bot', text };
      //{ sender: 'bot', text: data.re || 'Sorry, something went wrong.' };
      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { sender: 'bot', text: '⚠️ Could not connect to backend.' }]);
    }

    setInput('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') sendMessage();
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.sender}`}><p style={{ whiteSpace: 'pre-line' }}>{msg.text}</p></div>
        ))}
      </div>
      <div className="input-area">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

export default App;
