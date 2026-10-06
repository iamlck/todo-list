import { usePlan } from '../context/PlanContext'
import { downloadFile, exportRows, rowsToCsv } from '../lib/export'

/** Download the whole plan, with progress and time, for use in a spreadsheet. */
export default function ExportData() {
  const { days, startDate } = usePlan()
  const stamp = new Date().toISOString().slice(0, 10)

  function exportCsv() {
    downloadFile(`learning-tracker-${stamp}.csv`, rowsToCsv(exportRows(days, startDate)), 'text/csv;charset=utf-8')
  }

  function exportJson() {
    const payload = { exported_at: new Date().toISOString(), start_date: startDate, days }
    downloadFile(`learning-tracker-${stamp}.json`, JSON.stringify(payload, null, 2), 'application/json')
  }

  return (
    <div className="row wrap gap">
      <button type="button" className="secondary" onClick={exportCsv} disabled={days.length === 0}>
        Export CSV
      </button>
      <button type="button" className="secondary" onClick={exportJson} disabled={days.length === 0}>
        Export JSON
      </button>
    </div>
  )
}
