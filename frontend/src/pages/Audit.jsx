import { useState, useEffect } from 'react'
import axios from 'axios'

export default function Audit() {
  const [logs, setLogs] = useState([])
  const [eventType, setEventType] = useState('')
  const [entityType, setEntityType] = useState('')
  const [loading, setLoading] = useState(false)

  async function fetchLogs() {
    setLoading(true)
    try {
      const params = {}
      if (eventType) params.event_type = eventType
      if (entityType) params.entity_type = entityType
      const res = await axios.get('/api/audit/logs', { params })
      setLogs(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchLogs() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <h1>Audit Log</h1>
      <div className="card" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="Event type filter"
          value={eventType}
          onChange={e => setEventType(e.target.value)}
          style={{ flex: 1, minWidth: 160, padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc' }}
        />
        <input
          type="text"
          placeholder="Entity type filter"
          value={entityType}
          onChange={e => setEntityType(e.target.value)}
          style={{ flex: 1, minWidth: 160, padding: '0.4rem 0.75rem', borderRadius: 4, border: '1px solid #ccc' }}
        />
        <button
          onClick={fetchLogs}
          disabled={loading}
          style={{ padding: '0.4rem 1rem', borderRadius: 4, background: '#1a1a2e', color: '#fff', border: 'none', cursor: 'pointer' }}
        >
          {loading ? 'Loading…' : 'Filter'}
        </button>
      </div>

      {logs.length === 0 ? (
        <p className="placeholder">No audit log entries.</p>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: '#f0f0f0' }}>
                <th style={th}>Timestamp</th>
                <th style={th}>Event</th>
                <th style={th}>Entity</th>
                <th style={th}>Entity ID</th>
                <th style={th}>Actor</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={td}>{new Date(log.timestamp).toLocaleString()}</td>
                  <td style={td}><code>{log.event_type}</code></td>
                  <td style={td}>{log.entity_type}</td>
                  <td style={td}>{log.entity_id ?? '—'}</td>
                  <td style={td}>{log.user_or_system}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

const th = { padding: '0.6rem 1rem', textAlign: 'left', fontWeight: 600 }
const td = { padding: '0.5rem 1rem' }
