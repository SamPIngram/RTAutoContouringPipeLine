import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const btn = (bg = '#1a1a2e') => ({
  padding: '0.35rem 0.8rem',
  borderRadius: 4,
  background: bg,
  color: '#fff',
  border: 'none',
  cursor: 'pointer',
  fontSize: '0.85rem',
})

export default function Datasets() {
  const [datasets, setDatasets] = useState([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [fingerprints, setFingerprints] = useState({})  // dataset_id → fingerprint
  const [fpLoading, setFpLoading] = useState({})
  const navigate = useNavigate()

  useEffect(() => {
    axios.get('/api/datasets').then(res => setDatasets(res.data)).catch(() => {})
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await axios.post('/api/datasets', { name, description, study_ids: [] })
      setDatasets(prev => [res.data, ...prev])
      setName('')
      setDescription('')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(id) {
    await axios.delete(`/api/datasets/${id}`)
    setDatasets(prev => prev.filter(d => d.id !== id))
    setFingerprints(prev => { const n = { ...prev }; delete n[id]; return n })
  }

  async function handleFingerprint(dataset) {
    setFpLoading(prev => ({ ...prev, [dataset.id]: 'computing' }))
    try {
      // Enqueue computation
      await axios.post(`/api/datasets/${dataset.id}/fingerprint`)
      setFpLoading(prev => ({ ...prev, [dataset.id]: 'queued' }))
    } catch (err) {
      const msg = err.response?.data?.detail ?? err.message
      setFpLoading(prev => ({ ...prev, [dataset.id]: `Error: ${msg}` }))
    }
  }

  async function handleLoadFingerprint(datasetId) {
    try {
      const res = await axios.get(`/api/datasets/${datasetId}/fingerprint`)
      setFingerprints(prev => ({ ...prev, [datasetId]: res.data }))
    } catch {
      setFingerprints(prev => ({ ...prev, [datasetId]: null }))
    }
  }

  return (
    <>
      <h1>Datasets</h1>

      <div className="card">
        <h2 style={{ marginBottom: '1rem', fontSize: '1rem' }}>New Dataset</h2>
        <form onSubmit={handleCreate} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Dataset name"
            value={name}
            onChange={e => setName(e.target.value)}
            style={{ flex: 1, minWidth: 160, padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc' }}
            required
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={description}
            onChange={e => setDescription(e.target.value)}
            style={{ flex: 2, minWidth: 200, padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc' }}
          />
          <button type="submit" disabled={loading} style={btn()}>Create</button>
        </form>
      </div>

      {datasets.length === 0 ? (
        <p className="placeholder">No datasets yet.</p>
      ) : (
        datasets.map(d => {
          const fp = fingerprints[d.id]
          const fpStatus = fpLoading[d.id]
          return (
            <div className="card" key={d.id}>
              {/* Header row */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <strong>{d.name}</strong>
                  {d.description && <p style={{ color: '#666', fontSize: '0.875rem' }}>{d.description}</p>}
                  <p style={{ color: '#888', fontSize: '0.8rem' }}>{d.study_ids.length} studies</p>
                </div>
                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                  <button onClick={() => handleFingerprint(d)} style={btn('#2c7a4b')}
                    title="Compute nnU-Net-style statistics for this dataset">
                    Fingerprint
                  </button>
                  <button onClick={() => handleLoadFingerprint(d.id)} style={btn('#555')}>
                    Load Stats
                  </button>
                  <button
                    onClick={() => navigate(`/guardrails?dataset=${d.id}`)}
                    style={btn('#6a1aab')}
                    title="Manage AI guardrails for this dataset"
                  >
                    Guardrails
                  </button>
                  <button onClick={() => handleDelete(d.id)} style={btn('#c0392b')}>Delete</button>
                </div>
              </div>

              {/* Fingerprint task status */}
              {fpStatus && (
                <p style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: fpStatus.startsWith('Error') ? 'red' : '#2c7a4b' }}>
                  {fpStatus === 'computing' ? 'Fingerprint task queued...' : fpStatus}
                </p>
              )}

              {/* Fingerprint stats panel */}
              {fp === null && (
                <p style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#888' }}>
                  No fingerprint computed yet.
                </p>
              )}
              {fp && (
                <div style={{ marginTop: '0.75rem', background: '#f8f8f8', borderRadius: 4, padding: '0.75rem', fontSize: '0.82rem' }}>
                  <strong>Dataset Fingerprint</strong>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.4rem', marginTop: '0.4rem' }}>
                    <Stat label="Images" value={fp.n_images} />
                    <Stat label="Median spacing (mm)" value={fp.spacing_median?.join(' × ')} />
                    <Stat label="Spacing p05 (mm)" value={fp.spacing_p05?.join(' × ')} />
                    <Stat label="Spacing p95 (mm)" value={fp.spacing_p95?.join(' × ')} />
                    <Stat label="Median size (vox)" value={fp.size_median?.join(' × ')} />
                    <Stat label="Intensity mean" value={fp.intensity_mean?.toFixed(1)} />
                    <Stat label="Intensity std" value={fp.intensity_std?.toFixed(1)} />
                    <Stat label="Intensity p05" value={fp.intensity_p05?.toFixed(1)} />
                    <Stat label="Intensity p95" value={fp.intensity_p95?.toFixed(1)} />
                    <Stat label="Modalities" value={fp.modalities?.join(', ') || '—'} />
                    <Stat label="Computed" value={new Date(fp.computed_at).toLocaleString()} />
                  </div>
                </div>
              )}
            </div>
          )
        })
      )}
    </>
  )
}

function Stat({ label, value }) {
  return (
    <div>
      <span style={{ color: '#888' }}>{label}: </span>
      <span style={{ fontWeight: 500 }}>{value ?? '—'}</span>
    </div>
  )
}
