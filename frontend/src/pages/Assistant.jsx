import { useState, useRef, useEffect } from "react";
import Navbar from "../components/Navbar";
import "./Assistant.css";

/* ------------------------------------------------------------------ */
/*  Configuration – pulled from Vite environment variable              */
/* ------------------------------------------------------------------ */
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

/* ------------------------------------------------------------------ */
/*  Starter question chips                                              */
/* ------------------------------------------------------------------ */
const STARTER_QUESTIONS = [
  { icon: "🌾", text: "What is AgriConnect AI?" },
  { icon: "🍅", text: "How can I sell tomatoes?" },
  { icon: "🚜", text: "How do I rent a tractor?" },
  { icon: "🚨", text: "How do I report a suspicious listing?" },
];

/* ------------------------------------------------------------------ */
/*  Component                                                           */
/* ------------------------------------------------------------------ */
export default function Assistant() {
  const [messages, setMessages] = useState([]);   // { role: "user"|"bot", text, sources }
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  /* Auto-scroll to latest message */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  /* ── Core send logic ─────────────────────────────────────────── */
  async function sendMessage(userText) {
    const text = (userText ?? input).trim();
    if (!text) return;

    // Clear input immediately
    setInput("");
    setError("");

    // Append user message to conversation
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);

    try {
      const res = await fetch(`${BACKEND_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error ${res.status}`);
      }

      const data = await res.json();

      // Append bot answer with optional sources
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: data.answer, sources: data.sources || [] },
      ]);
    } catch (err) {
      const msg = err.message.includes("fetch")
        ? "Cannot reach the backend. Please make sure the FastAPI server is running at " + BACKEND_URL
        : err.message;
      setError(msg);
      // Show error as bot message too so conversation stays intact
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "⚠ " + msg, sources: [] },
      ]);
    } finally {
      setLoading(false);
    }
  }

  /* ── Handle Enter key in input ───────────────────────────────── */
  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="assist-page">
      <Navbar />

      {/* ── Hero banner ─────────────────────────────────────────── */}
      <header className="assist-hero">
        <p className="assist-eyebrow">AI ASSISTANT</p>
        <h1 className="assist-title">
          AgriConnect <span>AI</span> Assistant
        </h1>
        <p className="assist-subtitle">
          Ask about selling crops, renting equipment, buying products, or platform rules.
        </p>
      </header>

      <main className="assist-main">
        {/* ── Starter chips ──────────────────────────────────────── */}
        {messages.length === 0 && (
          <div className="assist-chips">
            <span className="assist-chips-label">Try asking…</span>
            {STARTER_QUESTIONS.map((q) => (
              <button
                key={q.text}
                className="assist-chip"
                onClick={() => sendMessage(q.text)}
                disabled={loading}
                type="button"
              >
                <span>{q.icon}</span>
                {q.text}
              </button>
            ))}
          </div>
        )}

        {/* ── Chat window ────────────────────────────────────────── */}
        <div className="assist-chat-window">
          {/* Message list */}
          <div className="assist-messages" role="log" aria-live="polite">
            {messages.length === 0 ? (
              <div className="assist-empty">
                <span className="assist-empty-icon">🤖</span>
                <h3>How can I help you today?</h3>
                <p>Use the chips above or type a question to get started.</p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`msg-row ${msg.role === "user" ? "user" : "bot"}`}>
                  {/* Avatar */}
                  <div className={`msg-avatar ${msg.role === "user" ? "user-av" : "bot-av"}`}>
                    {msg.role === "user" ? "👤" : "🌾"}
                  </div>

                  {/* Bubble + sources */}
                  <div className="msg-bubble-wrap">
                    <div className="msg-bubble">{msg.text}</div>
                    {msg.role === "bot" && msg.sources && msg.sources.length > 0 && (
                      <span className="msg-source">
                        📄 Source: {msg.sources.join(", ")}
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}

            {/* Loading indicator bubble */}
            {loading && (
              <div className="msg-row bot">
                <div className="msg-avatar bot-av">🌾</div>
                <div className="msg-bubble-wrap">
                  <div className="msg-bubble loading">
                    <span className="dot-flashing" />
                    <span className="dot-flashing" />
                    <span className="dot-flashing" />
                  </div>
                </div>
              </div>
            )}

            {/* Scroll anchor */}
            <div ref={bottomRef} />
          </div>

          {/* Backend error banner */}
          {error && (
            <div className="assist-error-bar" role="alert">
              ⚠ {error}
            </div>
          )}

          {/* Input row */}
          <div className="assist-input-row">
            <input
              id="assist-input"
              className="assist-input"
              type="text"
              placeholder="Type your question…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              aria-label="Chat message input"
              autoComplete="off"
            />
            <button
              id="assist-send-btn"
              className="assist-send-btn"
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
              aria-label="Send message"
              type="button"
            >
              ➤
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
