import { useEffect, useState } from 'react'
import { deleteDocument, listDocuments, type Document } from './api'
import { DocumentList } from './components/DocumentList'
import { UploadPanel } from './components/UploadPanel'

function App() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    listDocuments()
      .then((docs) => {
        if (!cancelled) setDocuments(docs)
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

      return () => {
        cancelled = true
      }  
  }, [])

  async function handleDelete(doc: Document) {
    if (!confirm(`Obrisati "${doc.title}" i sve njegove chunkove?`)) return
    
    try {
      await deleteDocument(doc.id)
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id))
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <main>
      <h1>ask-your-docs</h1>
      {error && <p className="error">{error}</p>}

      <UploadPanel onCreated={(doc) => setDocuments((prev) => [doc, ...prev])} />

      {loading ? (
        <p className="muted">Ucitavam...</p>
      ) : (
        <DocumentList documents={documents} onDelete={handleDelete} />
      )}
    </main>
  )
}

export default App
