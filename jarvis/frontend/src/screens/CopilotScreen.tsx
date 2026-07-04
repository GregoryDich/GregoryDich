import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

type Msg = { role: 'user' | 'assistant'; content: string }

/** AI: копайлот над данными терминала (полный режим при ANTHROPIC_API_KEY). */
export default function CopilotScreen() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [llmEnabled, setLlmEnabled] = useState<boolean | null>(null)
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.aiStatus().then((s) => setLlmEnabled(s.llm_enabled)).catch(() => setLlmEnabled(false))
  }, [])

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight })
  }, [messages])

  const send = async (text?: string) => {
    const msg = (text ?? input).trim()
    if (!msg || busy) return
    setInput('')
    setBusy(true)
    setMessages((m) => [...m, { role: 'user', content: msg }])
    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }))
      const r = await api.aiChat(msg, history)
      setMessages((m) => [...m, { role: 'assistant', content: r.reply }])
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: `Ошибка: ${e}` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="screen chat">
      <div className="card" style={{ marginBottom: 8 }}>
        <h3>
          AI Copilot{' '}
          {llmEnabled === false && (
            <span className="badge demo">фолбэк-режим — добавьте ANTHROPIC_API_KEY в .env</span>
          )}
          {llmEnabled && <span className="badge live">LLM активен</span>}
        </h3>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {['Как мой портфель?', 'Далеко до свободы?', 'Что на рынках?'].map((q) => (
            <button key={q} className="ghost" onClick={() => send(q)}>{q}</button>
          ))}
        </div>
      </div>
      <div className="chat-log" ref={logRef}>
        {messages.length === 0 && (
          <div className="muted" style={{ padding: 20, textAlign: 'center' }}>
            Спросите о портфеле, свободе или рынках. С ключом — любой вопрос к вашим данным
            («почему упал портфель на этой неделе?», «покажи мои худшие позиции SQL-запросом»).
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role === 'user' ? 'user' : 'bot'}`}>{m.content}</div>
        ))}
        {busy && <div className="msg bot muted">думаю…</div>}
      </div>
      <div className="chat-input">
        <input
          value={input}
          placeholder="Вопрос к JARVIS…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
        />
        <button className="primary" onClick={() => send()}>→</button>
      </div>
    </div>
  )
}
