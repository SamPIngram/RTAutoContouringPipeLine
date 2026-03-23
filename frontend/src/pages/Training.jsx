import { useState } from 'react'
import axios from 'axios'

export default function Training() {
  const [datasetId, setDatasetId] = useState('')
  const [modelName, setModelName] = useState('')
  const [framework, setFramework] = useState('nnunet')
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleStart(e) {
    e.preventDefault()
    setLoading(true)
    setStatus(null)
    try {
      const res = await axios.post('/api/training/start', {
        dataset_id: parseInt(datasetId),
        model_name: modelName,
        framework,
      })
      setJobId(res.data.job_id)
      setStatus({ ok: true, message: `Job queued: ${res.data.job_id}` })
    } catch (err) {
      setStatus({ ok: false, message: err.response?.data?.detail ?? err.message })
    } finally {
      setLoading(false)
    }
  }

  async function handlePoll() {
    if (!jobId) return
    try {
      const res = await axios.get(`/api/training/${jobId}/status`)
      setStatus({ ok: true, message: `Status: ${res.data.status}` })
    } catch (err) {
      setStatus({ ok: false, message: err.response?.data?.detail ?? err.message })
    }
  }

  return (
    <>
      <h1>Training</h1>
      <div className="card">
        <h2 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Start Training Job</h2>
        <form onSubmit={handleStart} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <input
            type="number"
            placeholder="Dataset ID"
            value={datasetId}
            onChange={e => setDatasetId(e.target.value)}
            style={{ width: 120, padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc' }}
            required
          />
          <input
            type="text"
            placeholder="Model name (e.g. Dataset001_Prostate)"
            value={modelName}
            onChange={e => setModelName(e.target.value)}
            style={{ flex: 1, minWidth: 200, padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc' }}
            required
          />
          <select
            value={framework}
            onChange={e => setFramework(e.target.value)}
            style={{ padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc' }}
          >
            <option value="nnunet">nnU-Net</option>
            <option value="monai">MONAI</option>
          </select>
          <button
            type="submit"
            disabled={loading}
            style={{ padding: '0.4rem 1rem', borderRadius: 4, background: '#1a1a2e', color: '#fff', border: 'none', cursor: 'pointer' }}
          >
            {loading ? 'Queuing…' : 'Start'}
          </button>
        </form>
        {status && (
          <p style={{ marginTop: '0.75rem', color: status.ok ? 'green' : 'red' }}>{status.message}</p>
        )}
        {jobId && (
          <button
            onClick={handlePoll}
            style={{ marginTop: '0.5rem', padding: '0.3rem 0.75rem', borderRadius: 4, background: '#444', color: '#fff', border: 'none', cursor: 'pointer' }}
          >
            Refresh Status
          </button>
        )}
      </div>
    </>
  )
}
