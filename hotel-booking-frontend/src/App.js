// src/App.js
import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

function App() {
  const STAGES = {
    BOOKING: "booking",
    SELECTING: "selecting",
    CONFIRMING: "confirming",
    DONE: "done",
  };

  const [messages, setMessages] = useState([
    {
      sender: "bot",
      text: "👋 Welcome to Hotel Bot! How can I help you today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [stage, setStage] = useState("booking");

  const changeStage = (newStage) => {
    console.log(`🔁 Stage changed from "${stage}" to "${newStage}"`);
    setStage(newStage);
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);

    let url = "";
    switch (stage) {
      case STAGES.BOOKING:
        url = "http://127.0.0.1:8000/request_hotel";
        break;
      case STAGES.SELECTING:
        url = "http://127.0.0.1:8000/select_hotel";
        break;
      case STAGES.CONFIRMING:
        url = "http://127.0.0.1:8000/book_hotel";
        break;
      default:
        console.error(`❌ No URL determined. Invalid stage: ${stage}`);
        return;
    }

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });

      console.log("URL:", url);
      const data = await res.json();
      console.log("🟢 Response:", data);

      // Handle errors
      if (data.error) {
        setMessages((prev) => [
          ...prev,
          { sender: "bot", text: `⚠️ ${data.error}` },
        ]);
        return;
      }

      // Use backend-supplied next_stage if available
      if (data.next_stage && Object.values(STAGES).includes(data.next_stage)) {
        changeStage(data.next_stage);
      }

      if (stage === STAGES.BOOKING) {
        const { summary, results, reply } = data;
        if (results) {
          changeStage(STAGES.SELECTING);
        }
        let botMsg = "";
        if (reply) {
          botMsg = reply;
        } else {
          botMsg = `${summary || ""}\n\n${results || ""}`;
        }
        setMessages((prev) => [...prev, { sender: "bot", text: botMsg }]);
      } else if (stage === STAGES.SELECTING) {
        if (data.message) {
          changeStage(STAGES.CONFIRMING);
          setMessages((prev) => [
            ...prev,
            { sender: "bot", text: data.message },
          ]);
        }
      } else if (stage === STAGES.CONFIRMING) {
        if (data.message) {
          changeStage(STAGES.DONE);
          setMessages((prev) => [
            ...prev,
            { sender: "bot", text: data.message },
          ]);

          // Optional: reset after booking
          setTimeout(() => {
            setMessages([
              {
                sender: "bot",
                text: "👋 Would you like to make another booking?",
              },
            ]);
            changeStage(STAGES.BOOKING);
          }, 5000);
        }
      }
    } catch (err) {
      console.error("❌ Network error:", err);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Could not connect to backend." },
      ]);
    }

    setInput("");
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.sender}`}>
            <ReactMarkdown>{msg.text}</ReactMarkdown>
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

export default App;
