import { useEffect, useMemo, useRef, useState } from 'react'

export type Command = {
  code: string // мнемоника Bloomberg-стиля: FIRE, WEI, PORT...
  title: string
  hint?: string
  run: () => void
}

/** Командная палитра: Ctrl/Cmd+K, мнемоники, стрелки + Enter. */
export default function Palette({ commands, open, onClose }: {
  commands: Command[]
  open: boolean
  onClose: () => void
}) {
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return commands
    return commands.filter(
      (c) => c.code.toLowerCase().startsWith(s) || c.title.toLowerCase().includes(s),
    )
  }, [q, commands])

  useEffect(() => {
    if (open) {
      setQ('')
      setSel(0)
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [open])

  if (!open) return null

  const runSelected = (i: number) => {
    filtered[i]?.run()
    onClose()
  }

  return (
    <div className="palette-overlay" onClick={onClose}>
      <div className="palette" onClick={(e) => e.stopPropagation()}>
        <input
          ref={inputRef}
          value={q}
          placeholder="Команда или мнемоника (FIRE, WEI, PORT, ECO…)"
          onChange={(e) => {
            setQ(e.target.value)
            setSel(0)
          }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') setSel((s) => Math.min(s + 1, filtered.length - 1))
            else if (e.key === 'ArrowUp') setSel((s) => Math.max(s - 1, 0))
            else if (e.key === 'Enter') runSelected(sel)
            else if (e.key === 'Escape') onClose()
          }}
        />
        {filtered.map((c, i) => (
          <div
            key={c.code + c.title}
            className={`item ${i === sel ? 'sel' : ''}`}
            onMouseEnter={() => setSel(i)}
            onClick={() => runSelected(i)}
          >
            <span className="code">{c.code}</span>
            <span>{c.title}</span>
            {c.hint && <span className="hint">{c.hint}</span>}
          </div>
        ))}
        {filtered.length === 0 && <div className="item muted">Ничего не найдено</div>}
      </div>
    </div>
  )
}
