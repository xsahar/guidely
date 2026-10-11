import { useEffect, useState } from 'react'
import './App.css'

const renderInlineMarkdown = (text) =>
  text.split(/(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*\n]+\*|_[^_\n]+_)/g).map((part, index) => {
    if ((part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))) {
      return <strong key={index}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={index}>{part.slice(1, -1)}</code>
    }
    if ((part.startsWith('*') && part.endsWith('*')) || (part.startsWith('_') && part.endsWith('_'))) {
      return <em key={index}>{part.slice(1, -1)}</em>
    }
    return part
  })

const formatFileSize = (bytes) =>
  bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`

const getRequestErrorMessage = (error, fallback) => {
  if (/failed to fetch|networkerror|load failed/i.test(error?.message || '')) {
    return 'Cannot connect to the Guidely backend at http://127.0.0.1:8000. Start it with `uvicorn backend.main:app --reload`, then try again.'
  }

  return error?.message || fallback
}

function App() {
  const [activeTab, setActiveTab] = useState('search') // 'search' or 'admin'
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  // Admin / Documents state
  const [documents, setDocuments] = useState([])
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState('')
  const [uploadError, setUploadError] = useState('')
  const [uploadFile, setUploadFile] = useState(null)

  const readApiError = async (response) => {
    const data = await response.json().catch(() => null)
    return data?.detail || `Request failed (${response.status}).`
  }

  const refreshDocuments = async () => {
    const response = await fetch('http://127.0.0.1:8000/documents')
    if (!response.ok) throw new Error(await readApiError(response))
    const data = await response.json()
    setDocuments(data.documents)
  }

  useEffect(() => {
    if (activeTab !== 'admin') return
    let cancelled = false
    setDocumentsLoading(true)
    fetch('http://127.0.0.1:8000/documents')
      .then(async (response) => {
        if (!response.ok) throw new Error(await readApiError(response))
        return response.json()
      })
      .then((data) => {
        if (!cancelled) setDocuments(data.documents)
      })
      .catch((requestError) => {
        if (!cancelled) {
          setUploadError(getRequestErrorMessage(requestError, 'Could not load the document list.'))
        }
      })
      .finally(() => {
        if (!cancelled) setDocumentsLoading(false)
      })
    return () => { cancelled = true }
  }, [activeTab])

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

      if (!response.ok) throw new Error(await readApiError(response))

      const data = await response.json()
      setResult(data)
    } catch (requestError) {
      setError(getRequestErrorMessage(requestError, 'Could not complete your search.'))
    } finally {
      setLoading(false)
    }
  }

  const handleReindex = async () => {
    setUploading(true)
    setUploadMsg('')
    setUploadError('')
    try {
      const response = await fetch('http://127.0.0.1:8000/documents/reindex', { method: 'POST' })
      if (!response.ok) throw new Error(await readApiError(response))
      const result = await response.json()
      await refreshDocuments()
      const cacheMessage = result.cache_hit
        ? 'Reused saved embeddings for unchanged files.'
        : `Generated embeddings for ${result.chunks_reembedded} chunks.`
      setUploadMsg(`Search index ready: ${result.documents} documents, ${result.chunks} chunks. ${cacheMessage}`)
    } catch (requestError) {
      setUploadError(getRequestErrorMessage(requestError, 'Re-indexing failed.'))
    } finally {
      setUploading(false)
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!uploadFile) {
      setUploadError('Choose a .txt file to upload.')
      return
    }

    setUploading(true)
    setUploadMsg('')
    setUploadError('')
    const formData = new FormData()
    formData.append('file', uploadFile)
    try {
      const response = await fetch('http://127.0.0.1:8000/documents/upload', {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) throw new Error(await readApiError(response))
      const result = await response.json()
      await refreshDocuments()
      setUploadMsg(`Indexed ${result.filename} (${result.chunks} chunks).`)
      setUploadFile(null)
      e.target.reset()
    } catch (requestError) {
      setUploadError(getRequestErrorMessage(requestError, 'Document upload failed.'))
    } finally {
      setUploading(false)
    }
  }

  const renderAnswer = (text) => {
    if (!text) return null

    const blocks = []
    let paragraph = []
    let listItems = []

    const flushParagraph = () => {
      if (paragraph.length) {
        blocks.push(<p key={`p-${blocks.length}`}>{renderInlineMarkdown(paragraph.join(' '))}</p>)
        paragraph = []
      }
    }
    const flushList = () => {
      if (listItems.length) {
        blocks.push(
          <ul key={`ul-${blocks.length}`}>
            {listItems.map((item, index) => <li key={index}>{renderInlineMarkdown(item)}</li>)}
          </ul>
        )
        listItems = []
      }
    }

    text.replace(/<br\s*\/?>/gi, '\n').split(/\r?\n/).forEach((line) => {
      const trimmedLine = line.trim()
      const heading = trimmedLine.match(/^(#{1,6})\s+(.+)$/)
      const bullet = trimmedLine.match(/^[-*+]\s+(.+)/)

      if (/^(?:-{2,}|_{3,}|\*{3,})$/.test(trimmedLine)) {
        flushParagraph()
        flushList()
      } else if (heading) {
        flushParagraph()
        flushList()
        const Heading = heading[1].length <= 3 ? 'h3' : 'h4'
        blocks.push(
          <Heading key={`h-${blocks.length}`}>
            {renderInlineMarkdown(heading[2])}
          </Heading>
        )
      } else if (bullet) {
        flushParagraph()
        listItems.push(bullet[1])
      } else if (!trimmedLine) {
        flushParagraph()
        flushList()
      } else {
        flushList()
        paragraph.push(trimmedLine)
      }
    })

    flushParagraph()
    flushList()
    return blocks
  }

  return (
    <div className="app-shell" style={{ maxWidth: '850px', margin: '40px auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', padding: '0 20px', color: '#e5e7eb' }}>

      {/* Header & Navigation */}
      <header className="app-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #374151', paddingBottom: '20px', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: '600', color: '#f3f4f6' }}>Guidely Knowledge Assistant</h1>
          <p style={{ margin: '4px 0 0 0', color: '#9ca3af', fontSize: '13px' }}>Internal RAG Knowledge Base</p>
        </div>
        <div className="app-nav" style={{ display: 'flex', gap: '10px', flexShrink: 0 }}>
          <button
            onClick={() => setActiveTab('search')}
            style={{ padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', backgroundColor: activeTab === 'search' ? '#2563eb' : '#374151', color: '#fff', border: 'none', fontWeight: '500', fontSize: '14px' }}
          >
            Ask a Question
          </button>
          <button
            onClick={() => setActiveTab('admin')}
            style={{ padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', backgroundColor: activeTab === 'admin' ? '#2563eb' : '#374151', color: '#fff', border: 'none', fontWeight: '500', fontSize: '14px' }}
          >
            Manage Documents
          </button>
        </div>
      </header>

      {/* View 1: Ask a Question */}
      {activeTab === 'search' ? (
        <div>
          <p style={{ color: '#9ca3af', fontSize: '14px', marginBottom: '16px' }}>Ask questions about company policies, or search with distinctive words from an uploaded document.</p>

          <form className="query-form" onSubmit={handleSearch} style={{ display: 'flex', gap: '10px', margin: '0 0 20px 0' }}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., How many PTO days do employees get?"
              style={{ flex: 1, padding: '12px 16px', fontSize: '15px', borderRadius: '8px', border: '1px solid #4b5563', backgroundColor: '#1f2937', color: '#fff', outline: 'none' }}
            />
            <button
              type="submit"
              disabled={loading}
              style={{ padding: '12px 24px', fontSize: '15px', borderRadius: '8px', cursor: 'pointer', backgroundColor: '#2563eb', color: '#fff', border: 'none', fontWeight: '500', flexShrink: 0 }}
            >
              {loading ? 'Searching...' : 'Ask'}
            </button>
          </form>

          {error && <div style={{ color: '#f87171', marginTop: '10px', padding: '12px', background: '#7f1d1d', borderRadius: '8px', fontSize: '14px' }}>{error}</div>}

          {result && (
            <div style={{ background: '#1f2937', border: '1px solid #374151', padding: '24px', borderRadius: '10px', marginTop: '20px', textAlign: 'left', color: '#f3f4f6' }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', color: '#60a5fa' }}>Answer:</h3>
              <div className="answer-content" style={{ lineHeight: '1.7', fontSize: '15px', color: '#d1d5db' }}>
                {renderAnswer(result.answer)}
              </div>

              {result.sources && result.sources.length > 0 && (
                <>
                  <h4 style={{ marginTop: '24px', marginBottom: '8px', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#9ca3af' }}>Sources:</h4>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {result.sources.map((src, i) => (
                      <span key={i} style={{ background: '#374151', border: '1px solid #4b5563', padding: '6px 12px', borderRadius: '6px', fontSize: '13px', color: '#e5e7eb' }}>
                        📄 {src}
                      </span>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      ) : (
        /* View 2: Manage Documents (Admin Page) */
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '6px' }}>Document Management & Admin Dashboard</h2>
          <p style={{ color: '#9ca3af', fontSize: '14px', marginBottom: '20px' }}>Upload a .txt file to add or replace a policy. Uploads are indexed immediately; re-index scans the saved files and refreshes the search index.</p>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '500' }}>Indexed Knowledge Base Files ({documents.length})</h3>
            <button
              onClick={handleReindex}
              disabled={uploading}
              style={{ padding: '10px 18px', borderRadius: '8px', cursor: 'pointer', backgroundColor: '#059669', color: '#fff', border: 'none', fontWeight: '500', fontSize: '14px' }}
            >
              {uploading ? 'Re-indexing...' : '🔄 Trigger Re-Index'}
            </button>
          </div>

          <form onSubmit={handleUpload} style={{ display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <input
              type="file"
              accept=".txt,text/plain"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              style={{ flex: 1, minWidth: '220px', color: '#d1d5db' }}
            />
            <button
              type="submit"
              disabled={uploading}
              style={{ padding: '10px 18px', borderRadius: '8px', cursor: 'pointer', backgroundColor: '#2563eb', color: '#fff', border: 'none', fontWeight: '500', fontSize: '14px' }}
            >
              {uploading ? 'Processing...' : 'Upload / Replace .txt'}
            </button>
          </form>

          {uploadMsg && <div style={{ margin: '12px 0', padding: '12px', background: '#064e3b', border: '1px solid #059669', color: '#34d399', borderRadius: '8px', fontSize: '14px' }}>{uploadMsg}</div>}
          {uploadError && <div role="alert" style={{ margin: '12px 0', padding: '12px', background: '#7f1d1d', border: '1px solid #b91c1c', color: '#fecaca', borderRadius: '8px', fontSize: '14px' }}>{uploadError}</div>}

          <div style={{ border: '1px solid #374151', borderRadius: '10px', overflow: 'hidden', background: '#1f2937' }}>
            <table className="document-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ background: '#111827', borderBottom: '1px solid #374151' }}>
                  <th style={{ padding: '12px 16px', fontSize: '13px', color: '#9ca3af', fontWeight: '600' }}>Filename</th>
                  <th style={{ padding: '12px 16px', fontSize: '13px', color: '#9ca3af', fontWeight: '600' }}>Size</th>
                  <th style={{ padding: '12px 16px', fontSize: '13px', color: '#9ca3af', fontWeight: '600' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {documentsLoading ? (
                  <tr><td colSpan="3" style={{ padding: '16px', color: '#9ca3af' }}>Loading documents...</td></tr>
                ) : documents.length === 0 ? (
                  <tr><td colSpan="3" style={{ padding: '16px', color: '#9ca3af' }}>No text documents are indexed.</td></tr>
                ) : documents.map((doc, idx) => (
                  <tr key={idx} style={{ borderBottom: idx < documents.length - 1 ? '1px solid #374151' : 'none' }}>
                    <td style={{ padding: '12px 16px', fontSize: '14px', fontWeight: '500', color: '#f3f4f6' }}>📄 {doc.name}</td>
                    <td style={{ padding: '12px 16px', fontSize: '14px', color: '#9ca3af' }}>{formatFileSize(doc.size)}</td>
                    <td style={{ padding: '12px 16px', fontSize: '14px', color: '#34d399', fontWeight: '600' }}>{doc.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export default App