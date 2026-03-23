import { useState, useEffect } from 'react'
import axios from 'axios'

export default function Datasets() {
  const [datasets, setDatasets] = useState([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)

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
          <button
            type="submit"
            disabled={loading}
            style={{ padding: '0.4rem 1rem', borderRadius: 4, background: '#1a1a2e', color: '#fff', border: 'none', cursor: 'pointer' }}
          >
            Create
          </button>
        </form>
      </div>

      {datasets.length === 0 ? (
        <p className="placeholder">No datasets yet.</p>
      ) : (
        datasets.map(d => (
          <div className="card" key={d.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <strong>{d.name}</strong>
              {d.description && <p style={{ color: '#666', fontSize: '0.875rem' }}>{d.description}</p>}
              <p style={{ color: '#888', fontSize: '0.8rem' }}>{d.study_ids.length} studies</p>
            </div>
            <button
              onClick={() => handleDelete(d.id)}
              style={{ padding: '0.3rem 0.75rem', borderRadius: 4, background: '#c0392b', color: '#fff', border: 'none', cursor: 'pointer' }}
            >
              Delete
            </button>
          </div>
        ))
      )}
    </>
  )
}
