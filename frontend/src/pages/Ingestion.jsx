import { useState } from 'react'
import axios from 'axios'

export default function Ingestion() {
  const [folderPath, setFolderPath] = useState('')
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleFolderIngest(e) {
    e.preventDefault()
    setLoading(true)
    setStatus(null)
    try {
      const res = await axios.post('/api/ingest/folder', {
        folder_path: folderPath,
        recursive: true,
      })
      setStatus({ ok: true, message: `Queued task ${res.data.task_id}` })
    } catch (err) {
      setStatus({ ok: false, message: err.response?.data?.detail ?? err.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <h1>Ingestion</h1>

      <div className="card">
        <h2 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Folder Ingest</h2>
        <form onSubmit={handleFolderIngest} style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            placeholder="/data/incoming/patient_001"
            value={folderPath}
            onChange={e => setFolderPath(e.target.value)}
            style={{ flex: 1, padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc' }}
            required
          />
          <button
            type="submit"
            disabled={loading}
            style={{ padding: '0.4rem 1rem', borderRadius: 4, background: '#1a1a2e', color: '#fff', border: 'none', cursor: 'pointer' }}
          >
            {loading ? 'Queuing…' : 'Ingest'}
          </button>
        </form>
        {status && (
          <p style={{ marginTop: '0.75rem', color: status.ok ? 'green' : 'red' }}>
            {status.message}
          </p>
        )}
      </div>

      <div className="card">
        <h2 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>Orthanc Webhook</h2>
        <p className="placeholder">
          Orthanc is configured to POST to <code>/api/orthanc/webhook</code> on new studies automatically.
        </p>
      </div>

      <div className="card">
        <h2 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>ProKnow Sync</h2>
        <p className="placeholder">ProKnow integration — configure credentials in config.toml.</p>
      </div>
    </>
  )
}
