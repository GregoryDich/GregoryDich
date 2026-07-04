import { useEffect, useState } from 'react'
import { api, type OnboardingQuestion } from '../api'

/** Онбординг-мастер: несколько вопросов → персональный профиль → терминал под вас. */
export default function Onboarding({ onDone }: { onDone: () => void }) {
  const [questions, setQuestions] = useState<OnboardingQuestion[]>([])
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, unknown>>({})

  useEffect(() => {
    api.onboarding().then((r) => setQuestions(r.questions)).catch(console.error)
  }, [])

  if (questions.length === 0) return null
  const q = questions[step]
  const value = answers[q.id]

  const set = (v: unknown) => setAnswers({ ...answers, [q.id]: v })

  const numericField = (fields: { k: string; label: string }[]) => {
    const obj = (value as Record<string, number>) ?? {}
    return fields.map((f) => (
      <div key={f.k}>
        <label>{f.label}</label>
        <input
          type="number"
          value={obj[f.k] ?? ''}
          onChange={(e) => set({ ...obj, [f.k]: +e.target.value || 0 })}
        />
      </div>
    ))
  }

  const finish = async () => {
    await api.saveProfile(answers)
    onDone()
  }

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>JARVIS — настройка под вас</h2>
        <div className="step">Шаг {step + 1} из {questions.length}</div>
        <b>{q.title}</b>
        {q.hint && <div className="sub">{q.hint}</div>}
        <div style={{ marginTop: 10 }}>
          {q.type === 'text' && (
            <input value={(value as string) ?? ''} onChange={(e) => set(e.target.value)} />
          )}
          {q.type === 'number' && (
            <input type="number" value={(value as number) ?? ''} onChange={(e) => set(+e.target.value || 0)} />
          )}
          {q.type === 'select' && (
            <select value={(value as string) ?? ''} onChange={(e) => set(e.target.value)}>
              <option value="" disabled>— выберите —</option>
              {q.options?.map((o) => <option key={o.v} value={o.v}>{o.label}</option>)}
            </select>
          )}
          {q.type === 'multiselect' && (
            <div className="chips">
              {q.options?.map((o) => {
                const arr = (value as string[]) ?? []
                const on = arr.includes(o.v)
                return (
                  <div
                    key={o.v}
                    className={`chip ${on ? 'on' : ''}`}
                    onClick={() => set(on ? arr.filter((x) => x !== o.v) : [...arr, o.v])}
                  >
                    {o.label}
                  </div>
                )
              })}
            </div>
          )}
          {(q.type === 'expenses' || q.type === 'capital') && q.fields && numericField(q.fields)}
        </div>
        <div className="row">
          {step > 0 && <button className="ghost" onClick={() => setStep(step - 1)}>Назад</button>}
          {step < questions.length - 1 ? (
            <button className="primary" onClick={() => setStep(step + 1)}>Далее</button>
          ) : (
            <button className="primary" onClick={finish}>Построить мой терминал</button>
          )}
        </div>
      </div>
    </div>
  )
}
