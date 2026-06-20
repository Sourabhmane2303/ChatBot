import { useState, useRef, useEffect } from "react"
import "./Chat.css"

const API = "http://localhost:8000"

const SUGGESTIONS = [
  "What are the objectives of this organization?",
  "What is the vision and mission?",
  "What are the key policies?",
  "Summarize this document",
]

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input,    setInput]    = useState("")
  const [loading,  setLoading]  = useState(false)
  const bottomRef               = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  async function sendMessage(question) {
    const q = question.trim()
    if (!q || loading) return

    setMessages(prev => [...prev, { role: "user", text: q }])
    setInput("")
    setLoading(true)

    try {
      const res  = await fetch(`${API}/ask`, {
        method  : "POST",
        headers : { "Content-Type": "application/json" },
        body    : JSON.stringify({ question: q,pdf_name: "bank.pdf"}),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Something went wrong")

      setMessages(prev => [...prev, {
        role   : "assistant",
        text   : data.answer,
        section: data.section,
        source : data.source,
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role : "assistant",
        text : `Error: ${err.message}`,
        error: true,
      }])
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <>
      <style>{css}</style>
      <div className="app">

        <header className="header">
          <span className="logo">⬡</span>
          <span className="logo-text">OrgIQ</span>
        </header>

        <div className="messages">
          {messages.length === 0 && (
            <div className="empty">
              <div className="empty-title">Ask anything about your organization</div>
              <div className="empty-sub">Try one of these to get started</div>
              <div className="suggestions">
                {SUGGESTIONS.map((s, i) => (
                  <button key={i} className="suggestion" onClick={() => sendMessage(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`msg ${msg.role} ${msg.error ? "msg-error" : ""}`}>
              <div className="bubble">
                <p className="bubble-text">{msg.text}</p>
                {msg.section && (
                  <div className="bubble-meta">
                    <span className="meta-tag">Section: {msg.section}</span>
                    {msg.source && <span className="meta-tag">Source: {msg.source}</span>}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="msg assistant">
              <div className="bubble">
                <div className="typing">
                  <span /><span /><span />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <div className="input-bar">
          <textarea
            className="input"
            placeholder="Ask a question…"
            value={input}
            rows={1}
            disabled={loading}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
          />
          <button
            className="send"
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
          >
            ↑
          </button>
        </div>

      </div>
    </>
  )
}

const css = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg      : #0d0f14;
    --surface : #13161f;
    --raised  : #1a1e2a;
    --input   : #1e2330;
    --border  : #252a3a;
    --accent  : #4a6cf7;
    --asoft   : rgba(74,108,247,0.12);
    --error   : rgba(241,96,96,0.1);
    --t1      : #eceef4;
    --t2      : #8892aa;
    --t3      : #4a5068;
    --r       : 12px;
    --rs      : 8px;
  }

  body {
    font-family: 'Inter', sans-serif;
    background : var(--bg);
    color      : var(--t1);
    height     : 100vh;
    overflow   : hidden;
    -webkit-font-smoothing: antialiased;
  }

  .app {
    display        : flex;
    flex-direction : column;
    height         : 100vh;
    max-width      : 780px;
    margin         : 0 auto;
  }

  .header {
    display     : flex;
    align-items : center;
    gap         : 10px;
    padding     : 18px 24px;
    border-bottom: 1px solid var(--border);
    flex-shrink : 0;
  }

  .logo      { font-size: 20px; color: var(--accent); }
  .logo-text { font-size: 16px; font-weight: 600; letter-spacing: -0.2px; }

  .messages {
    flex       : 1;
    overflow-y : auto;
    padding    : 28px 24px;
    display    : flex;
    flex-direction: column;
    gap        : 16px;
  }

  .messages::-webkit-scrollbar       { width: 4px; }
  .messages::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

  .empty {
    margin    : auto;
    text-align: center;
    max-width : 500px;
  }

  .empty-title {
    font-size    : 20px;
    font-weight  : 600;
    color        : var(--t1);
    margin-bottom: 8px;
  }

  .empty-sub {
    font-size    : 14px;
    color        : var(--t2);
    margin-bottom: 20px;
  }

  .suggestions {
    display       : flex;
    flex-direction: column;
    gap           : 8px;
  }

  .suggestion {
    background   : var(--raised);
    border       : 1px solid var(--border);
    border-radius: var(--rs);
    padding      : 11px 16px;
    text-align   : left;
    font-size    : 13px;
    color        : var(--t2);
    cursor       : pointer;
    transition   : border-color 0.15s, color 0.15s;
    font-family  : inherit;
  }

  .suggestion:hover { border-color: var(--accent); color: var(--t1); }

  .msg {
    display  : flex;
    max-width: 80%;
  }

  .msg.user      { align-self: flex-end; }
  .msg.assistant { align-self: flex-start; }

  .bubble {
    background    : var(--raised);
    border        : 1px solid var(--border);
    border-radius : var(--r);
    padding       : 12px 16px;
    display       : flex;
    flex-direction: column;
    gap           : 8px;
  }

  .msg.user .bubble     { background: var(--asoft); border-color: var(--accent); }
  .msg.msg-error .bubble { background: var(--error); border-color: #f16060; }

  .bubble-text {
    font-size : 14px;
    line-height: 1.65;
    color     : var(--t1);
    white-space: pre-wrap;
  }

  .bubble-meta { display: flex; gap: 6px; flex-wrap: wrap; }

  .meta-tag {
    font-size    : 11px;
    color        : var(--accent);
    background   : var(--asoft);
    padding      : 2px 8px;
    border-radius: 4px;
  }

  .typing { display: flex; gap: 5px; padding: 2px 0; }

  .typing span {
    width        : 7px;
    height       : 7px;
    border-radius: 50%;
    background   : var(--t3);
    animation    : bounce 1.2s ease-in-out infinite;
  }

  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }

  @keyframes bounce {
    0%, 80%, 100% { transform: translateY(0);    opacity: 0.4; }
    40%           { transform: translateY(-6px); opacity: 1;   }
  }

  .input-bar {
    display    : flex;
    gap        : 10px;
    align-items: flex-end;
    padding    : 16px 24px 24px;
    border-top : 1px solid var(--border);
    flex-shrink: 0;
  }

  .input {
    flex         : 1;
    background   : var(--input);
    border       : 1px solid var(--border);
    border-radius: var(--r);
    padding      : 12px 16px;
    font-size    : 14px;
    color        : var(--t1);
    resize       : none;
    line-height  : 1.5;
    max-height   : 120px;
    transition   : border-color 0.15s;
  }

  .input:focus        { outline: none; border-color: var(--accent); }
  .input::placeholder { color: var(--t3); }
  .input:disabled     { opacity: 0.4; cursor: not-allowed; }

  .send {
    width          : 42px;
    height         : 42px;
    border-radius  : var(--rs);
    background     : var(--accent);
    color          : white;
    font-size      : 18px;
    flex-shrink    : 0;
    transition     : opacity 0.15s, transform 0.1s;
    display        : flex;
    align-items    : center;
    justify-content: center;
    border         : none;
    cursor         : pointer;
  }

  .send:hover:not(:disabled)  { opacity: 0.85; }
  .send:active:not(:disabled) { transform: scale(0.94); }
  .send:disabled              { opacity: 0.25; cursor: not-allowed; }
`
