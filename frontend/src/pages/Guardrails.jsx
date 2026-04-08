import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
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

export default function Guardrails() {
  const [searchParams] = useSearchParams()
  const preselectedDataset = searchParams.get('dataset')

  const [datasets, setDatasets] = useState([])
  const [selectedDataset, setSelectedDataset] = useState(preselectedDataset || '')
  const [fingerprint, setFingerprint] = useState(null)
  const [fpError, setFpError] = useState(null)
  const [guardrails, setGuardrails] = useState([])
  const [allGuardrails, setAllGuardrails] = useState([])

  // Form state
  const [name, setName] = useState('')
  const [modalities, setModalities] = useState('MR')
  const [blockOnFailure, setBlockOnFailure] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState(null)

  // YAML viewer
  const [viewingYaml, setViewingYaml] = useState(null)  // guardrail id

  useEffect(() => {
    axios.get('/api/datasets').then(r => setDatasets(r.data)).catch(() => {})
    axios.get('/api/guardrails').then(r => setAllGuardrails(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedDataset) return
    setFingerprint(null)
    setFpError(null)
    setGuardrails([])
    axios.get(`/api/datasets/${selectedDataset}/fingerprint`)
      .then(r => setFingerprint(r.data))
      .catch(() => setFpError('No fingerprint computed yet. Go to Datasets and click Fingerprint.'))
    axios.get(`/api/datasets/${selectedDataset}/guardrails`)
      .then(r => setGuardrails(r.data))
      .catch(() => {})
  }, [selectedDataset])

  async function handleGenerate(e) {
    e.preventDefault()
    setGenerating(true)
    setGenError(null)
    try {
      const res = await axios.post(`/api/datasets/${selectedDataset}/guardrails`, {
        name,
        modalities: modalities.split(',').map(m => m.trim()).filter(Boolean),
        block_on_failure: blockOnFailure,
      })
      setGuardrails(prev => [res.data, ...prev])
      setAllGuardrails(prev => [res.data, ...prev])
      setName('')
    } catch (err) {
      setGenError(err.response?.data?.detail ?? err.message)
    } finally {
      setGenerating(false)
    }
  }

  async function handleDelete(id) {
    await axios.delete(`/api/guardrails/${id}`)
    setGuardrails(prev => prev.filter(g => g.id !== id))
    setAllGuardrails(prev => prev.filter(g => g.id !== id))
    if (viewingYaml === id) setViewingYaml(null)
  }

  async function handleDownload(g) {
    const res = await axios.get(`/api/guardrails/${g.id}/yaml`)
    const blob = new Blob([res.data], { type: 'text/yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${g.name}.yaml`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <h1>AI Guardrails</h1>
      <p style={{ color: '#555', marginBottom: '1rem', fontSize: '0.9rem' }}>
        Generate <a href="https://pypi.org/project/healthcare-ai-guardrails/" target="_blank" rel="noreferrer">healthcare-ai-guardrails</a> YAML
        configs from dataset fingerprint statistics. Apply them at inference time to catch out-of-distribution studies.
      </p>

      {/* Dataset selector */}
      <div className="card">
        <label style={{ fontWeight: 600 }}>Dataset</label>
        <select
          value={selectedDataset}
          onChange={e => setSelectedDataset(e.target.value)}
          style={{ display: 'block', marginTop: '0.4rem', padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc', width: '100%' }}
        >
          <option value="">— select a dataset —</option>
          {datasets.map(d => <option key={d.id} value={d.id}>{d.name} (id={d.id})</option>)}
        </select>
      </div>

      {/* Fingerprint summary */}
      {selectedDataset && (
        fpError
          ? <p style={{ color: '#c0392b', fontSize: '0.88rem' }}>{fpError}</p>
          : fingerprint && (
            <div className="card" style={{ background: '#f0f7f1', borderLeft: '4px solid #2c7a4b' }}>
              <strong>Fingerprint available</strong>
              <p style={{ fontSize: '0.83rem', marginTop: '0.3rem', color: '#444' }}>
                {fingerprint.n_images} images &nbsp;·&nbsp;
                Median spacing: {fingerprint.spacing_median?.join(' × ')} mm &nbsp;·&nbsp;
                Intensity p05–p95: {fingerprint.intensity_p05?.toFixed(1)} → {fingerprint.intensity_p95?.toFixed(1)}
              </p>
            </div>
          )
      )}

      {/* Generate form */}
      {selectedDataset && fingerprint && (
        <div className="card">
          <h2 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Generate New Guardrail Config</h2>
          <form onSubmit={handleGenerate} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div style={{ flex: 1, minWidth: 160 }}>
              <label style={{ fontSize: '0.8rem', color: '#555' }}>Config name</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. prostate_t2_guardrails"
                required
                style={{ display: 'block', width: '100%', padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc', marginTop: 2 }}
              />
            </div>
            <div style={{ flex: 1, minWidth: 140 }}>
              <label style={{ fontSize: '0.8rem', color: '#555' }}>Allowed modalities (comma-separated)</label>
              <input
                type="text"
                value={modalities}
                onChange={e => setModalities(e.target.value)}
                placeholder="MR, CT"
                style={{ display: 'block', width: '100%', padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc', marginTop: 2 }}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', paddingBottom: 2 }}>
              <input
                type="checkbox"
                id="blockOnFailure"
                checked={blockOnFailure}
                onChange={e => setBlockOnFailure(e.target.checked)}
              />
              <label htmlFor="blockOnFailure" style={{ fontSize: '0.8rem', color: '#555' }}>
                Block inference on failure
              </label>
            </div>
            <button type="submit" disabled={generating} style={btn('#6a1aab')}>
              {generating ? 'Generating…' : 'Generate YAML'}
            </button>
          </form>
          {genError && <p style={{ color: 'red', marginTop: '0.5rem', fontSize: '0.85rem' }}>{genError}</p>}
        </div>
      )}

      {/* Guardrail list for selected dataset */}
      {guardrails.length > 0 && (
        <>
          <h2 style={{ fontSize: '1rem', margin: '1rem 0 0.5rem' }}>Configs for this dataset</h2>
          {guardrails.map(g => (
            <GuardrailCard
              key={g.id}
              g={g}
              viewingYaml={viewingYaml}
              setViewingYaml={setViewingYaml}
              onDelete={handleDelete}
              onDownload={handleDownload}
            />
          ))}
        </>
      )}

      {/* All guardrails reference table */}
      {allGuardrails.length > 0 && (
        <>
          <h2 style={{ fontSize: '1rem', margin: '1.5rem 0 0.5rem' }}>All Guardrail Configs</h2>
          <div className="card" style={{ padding: 0, overflow: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: '#f0f0f0' }}>
                  {['ID', 'Name', 'Dataset', 'Created', 'YAML path'].map(h => (
                    <th key={h} style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {allGuardrails.map(g => (
                  <tr key={g.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '0.45rem 0.75rem' }}>{g.id}</td>
                    <td style={{ padding: '0.45rem 0.75rem' }}>{g.name}</td>
                    <td style={{ padding: '0.45rem 0.75rem' }}>#{g.dataset_id}</td>
                    <td style={{ padding: '0.45rem 0.75rem' }}>{new Date(g.created_at).toLocaleDateString()}</td>
                    <td style={{ padding: '0.45rem 0.75rem', fontFamily: 'monospace', fontSize: '0.78rem' }}>
                      {g.yaml_path ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  )
}

function GuardrailCard({ g, viewingYaml, setViewingYaml, onDelete, onDownload }) {
  const [yaml, setYaml] = useState(null)

  async function toggleYaml() {
    if (viewingYaml === g.id) {
      setViewingYaml(null)
      return
    }
    if (!yaml) {
      const res = await axios.get(`/api/guardrails/${g.id}/yaml`)
      setYaml(res.data)
    }
    setViewingYaml(g.id)
  }

  return (
    <div className="card" style={{ borderLeft: '4px solid #6a1aab' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <strong>{g.name}</strong>
          <p style={{ fontSize: '0.8rem', color: '#666', marginTop: 2 }}>
            Created {new Date(g.created_at).toLocaleString()}
            {g.yaml_path && <> &nbsp;·&nbsp; <code style={{ fontSize: '0.75rem' }}>{g.yaml_path}</code></>}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button onClick={toggleYaml} style={{ ...btn('#555'), background: viewingYaml === g.id ? '#333' : '#555' }}>
            {viewingYaml === g.id ? 'Hide YAML' : 'View YAML'}
          </button>
          <button onClick={() => onDownload(g)} style={btn('#2c7a4b')}>Download</button>
          <button onClick={() => onDelete(g.id)} style={btn('#c0392b')}>Delete</button>
        </div>
      </div>
      {viewingYaml === g.id && yaml && (
        <pre style={{
          marginTop: '0.75rem',
          background: '#1e1e2e',
          color: '#cdd6f4',
          padding: '0.75rem',
          borderRadius: 4,
          fontSize: '0.78rem',
          overflowX: 'auto',
          maxHeight: 400,
        }}>
          {yaml}
        </pre>
      )}
    </div>
  )
}
