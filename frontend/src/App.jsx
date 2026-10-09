import { useState } from 'react'
import './App.css'

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const response = await fetch('http://127.0.0.1:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`)
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError('Failed to reach Guidely API. Ensure backend is running.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: '700px', margin: '40px auto', fontFamily: 'sans-serif', padding: '0 20px' }}>
      <h1>Guidely Knowledge Assistant</h1>
      <p style={{ color: '#666' }}>Ask questions about company PTO, remote work, or security policies.</p>

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '10px', margin: '20px 0' }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., How many PTO days do employees get?"
          style={{ flex: 1, padding: '12px', fontSize: '16px', borderRadius: '6px', border: '1px solid #ccc' }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{ padding: '12px 24px', fontSize: '16px', borderRadius: '6px', cursor: 'pointer', backgroundColor: '#0070f3', color: '#fff', border: 'none' }}
        >
          {loading ? 'Searching...' : 'Ask'}
        </button>
      </form>

      {error && <div style={{ color: 'red', marginTop: '10px' }}>{error}</div>}

      {result && (
        <div style={{ background: '#f5f5f5', padding: '20px', borderRadius: '8px', marginTop: '20px', textAlign: 'left', color: '#111' }}>
          <h3>Answer:</h3>
          <p style={{ lineHeight: '1.6', whiteSpace: 'pre-line' }}>{result.answer}</p>

          <h4 style={{ marginTop: '20px', marginBottom: '8px' }}>Sources:</h4>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {result.sources.map((src, i) => (
              <span key={i} style={{ background: '#e0e0e0', padding: '4px 10px', borderRadius: '12px', fontSize: '14px', color: '#333' }}>
                📄 {src}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default App