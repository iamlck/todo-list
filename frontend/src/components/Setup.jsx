import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { usePlan } from '../context/PlanContext'
import { TEMPLATE_CSV, parsePlanCsv } from '../lib/csv'

const MODES = [
  {
    key: 'default',
    label: 'Use the default plan',
    blurb:
      '20 days covering AWS CloudOps, Kubernetes and GenAI, from foundations through a capstone to the exam. Fully editable afterwards.',
  },
  {
    key: 'blank',
    label: 'Choose a number of days',
    blurb: 'Start with empty days and add your own main tasks and subtasks as you go.',
  },
  {
    key: 'import',
    label: 'Upload a spreadsheet',
    blurb: 'Bring a plan you already have, as a CSV exported from Excel or Google Sheets.',
  },
]

export default function Setup() {
  const { reload } = usePlan()
  const navigate = useNavigate()

  const [mode, setMode] = useState('default')
  const [dayCount, setDayCount] = useState(20)
  const [parsed, setParsed] = useState(null)
  const [fileName, setFileName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  function downloadTemplate() {
    const blob = new Blob([TEMPLATE_CSV], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'learning-tracker-template.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  async function handleFile(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setFileName(file.name)
    setError(null)
    // Parsed in the browser so you see exactly what will be created before
    // anything is saved.
    setParsed(parsePlanCsv(await file.text()))
  }

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      if (mode === 'default') {
        await api.setupPlan({ mode: 'default' })
      } else if (mode === 'blank') {
        await api.setupPlan({ mode: 'blank', day_count: Number(dayCount) })
      } else {
        if (!parsed?.days.length) {
          setError('Choose a CSV file with at least one valid row first.')
          setBusy(false)
          return
        }
        await api.setupPlan({ mode: 'import', days: parsed.days })
      }
      await reload()
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  const totalTasks = parsed?.days.reduce((s, d) => s + d.tasks.length, 0) ?? 0
  const totalSubtasks =
    parsed?.days.reduce((s, d) => s + d.tasks.reduce((n, t) => n + t.subtasks.length, 0), 0) ?? 0

  return (
    <div className="pad stack">
      <section className="card stack">
        <h1>Set up your plan</h1>
        <p className="muted">
          Pick a starting point. Everything is editable later — days, main tasks and subtasks.
        </p>

        <fieldset className="setup-modes">
          <legend className="visually-hidden">How to start</legend>
          {MODES.map((option) => (
            <label key={option.key} className={`setup-mode${mode === option.key ? ' chosen' : ''}`}>
              <input
                type="radio"
                name="setup-mode"
                value={option.key}
                checked={mode === option.key}
                onChange={() => setMode(option.key)}
              />
              <span>
                <strong>{option.label}</strong>
                <br />
                <span className="muted small">{option.blurb}</span>
              </span>
            </label>
          ))}
        </fieldset>
      </section>

      {mode === 'blank' && (
        <section className="card stack narrow">
          <label htmlFor="day-count">How many days?</label>
          <input
            id="day-count"
            type="number"
            min={1}
            max={365}
            value={dayCount}
            onChange={(e) => setDayCount(e.target.value)}
          />
          <p className="muted small">You can add or remove days at any time.</p>
        </section>
      )}

      {mode === 'import' && (
        <section className="card stack">
          <h2>Upload a CSV</h2>
          <p className="muted small">
            Columns: <code>day, day_title, main_task, subtask</code> — one row per subtask,
            repeating the day and main task. Excel and Google Sheets both export CSV.
          </p>
          <div className="row gap wrap">
            <button type="button" className="secondary" onClick={downloadTemplate}>
              Download template
            </button>
            <input type="file" accept=".csv,text/csv" onChange={handleFile} aria-label="CSV file" />
          </div>

          {parsed && (
            <div className="stack">
              <h3>
                Preview {fileName && <span className="muted small">({fileName})</span>}
              </h3>
              {parsed.errors.length > 0 && (
                <ul className="error">
                  {parsed.errors.slice(0, 5).map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                  {parsed.errors.length > 5 && <li>…and {parsed.errors.length - 5} more.</li>}
                </ul>
              )}
              {parsed.days.length > 0 ? (
                <>
                  <p className="muted">
                    {parsed.days.length} days · {totalTasks} main tasks · {totalSubtasks} subtasks
                  </p>
                  <ul className="preview">
                    {parsed.days.slice(0, 3).map((day, i) => (
                      <li key={i}>
                        <strong>
                          Day {i + 1}
                          {day.title ? ` — ${day.title}` : ''}
                        </strong>
                        <ul>
                          {day.tasks.map((task) => (
                            <li key={task.title}>
                              {task.title}{' '}
                              <span className="muted small">({task.subtasks.length} subtasks)</span>
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                    {parsed.days.length > 3 && (
                      <li className="muted">…and {parsed.days.length - 3} more days.</li>
                    )}
                  </ul>
                </>
              ) : (
                <p className="muted">Nothing usable in that file yet.</p>
              )}
            </div>
          )}
        </section>
      )}

      <section className="card stack">
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button type="button" className="primary" onClick={submit} disabled={busy}>
          {busy ? 'Creating…' : 'Create my plan'}
        </button>
      </section>
    </div>
  )
}
