import { useState, useEffect } from 'react'
import axios from 'axios'

const DEFAULT_TOML = `[workflow]
name = "My_Deployment"
active = true
trigger = "orthanc_new_study"

[filtering]
modality = "MR"
series_description_regex = ".*t2.*"

[inference]
model_id = "nnunet_model_v1"
fallback_to_cpu = true

[export]
generate_rtstruct = true
rtstruct_name = "AI_Contours"
destination_type = "dicom_node"
destination_aet = "CLINICAL_TPS"
`

export default function Deployments() {
  const [deployments, setDeployments] = useState([])
  const [name, setName] = useState('')
  const [toml, setToml] = useState(DEFAULT_TOML)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    axios.get('/api/deployments').then(res => setDeployments(res.data)).catch(() => {})
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await axios.post('/api/deployments', { name, toml_config: toml })
      setDeployments(prev => [res.data, ...prev])
      setName('')
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message)
    } finally {
      setLoading(false)
    }
  }

  async function toggleActive(id, current) {
    const res = await axios.post(`/api/deployments/${id}/activate?active=${!current}`)
    setDeployments(prev => prev.map(d => d.id === id ? { ...d, active: res.data.active } : d))
  }

  async function handleDelete(id) {
    await axios.delete(`/api/deployments/${id}`)
    setDeployments(prev => prev.filter(d => d.id !== id))
  }

  return (
    <>
      <h1>Deployments</h1>
      <div className="card">
        <h2 style={{ marginBottom: '1rem', fontSize: '1rem' }}>New Deployment</h2>
        <form onSubmit={handleCreate}>
          <input
            type="text"
            placeholder="Deployment name"
            value={name}
            onChange={e => setName(e.target.value)}
            style={{ width: '100%', padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc', marginBottom: '0.5rem' }}
            required
          />
          <textarea
            value={toml}
            onChange={e => setToml(e.target.value)}
            rows={14}
            style={{ width: '100%', fontFamily: 'monospace', fontSize: '0.85rem', padding: '0.5rem', borderRadius: 4, border: '1px solid #ccc', marginBottom: '0.5rem' }}
          />
          {error && <p style={{ color: 'red', marginBottom: '0.5rem' }}>{error}</p>}
          <button
            type="submit"
            disabled={loading}
            style={{ padding: '0.4rem 1rem', borderRadius: 4, background: '#1a1a2e', color: '#fff', border: 'none', cursor: 'pointer' }}
          >
            Create
          </button>
        </form>
      </div>

      {deployments.map(d => (
        <div className="card" key={d.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <strong>{d.name}</strong>
            <p style={{ fontSize: '0.8rem', color: '#666' }}>Trigger: {d.trigger_type} · Model: {d.model_id ?? '—'}</p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => toggleActive(d.id, d.active)}
              style={{ padding: '0.3rem 0.75rem', borderRadius: 4, background: d.active ? '#27ae60' : '#888', color: '#fff', border: 'none', cursor: 'pointer' }}
            >
              {d.active ? 'Active' : 'Inactive'}
            </button>
            <button
              onClick={() => handleDelete(d.id)}
              style={{ padding: '0.3rem 0.75rem', borderRadius: 4, background: '#c0392b', color: '#fff', border: 'none', cursor: 'pointer' }}
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </>
  )
}
