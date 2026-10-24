import { useState } from 'react'
import { createTextDocument, uploadDocument, type Document } from '../api'

type Props = {
  onCreated: (doc: Document) => void
}

export function UploadPanel({ onCreated }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [text, setText] = useState('')
  const [title, setTitle] = useState('')

  //busy cuva od duplog slanja: dva klika = dva dokumenta i dvaput placen embedding
  async function send(action: () => Promise<Document>): Promise<boolean> {
    setBusy(true)
    setError(null)
    try {
      onCreated(await action())
      return true
    } catch (err) {
      setError((err as Error).message)
      return false
    } finally {
      setBusy(false)
    }
  }

  async function handleFiles(files: FileList | null) {
    if (!files) return
    //sekvencijalno, da pet fajlova ne postane pet paralelnih poziva OpenAI-ju
    for (const file of Array.from(files)) {
      await send(() => uploadDocument(file))
    }
  }

  async function handleText() {
    if (!text.trim()) return
    const ok = await send(() => createTextDocument(text, title.trim() || undefined))
    if (ok) {
      setText('')
      setTitle('')
    }
  }

  return (
    <section className="panel">
      <h2>Dodaj dokument</h2>

      <div
        className={dragging ? 'dropzone dragging' : 'dropzone'}
        onDragOver={(e) => {
          //bez preventDefault browser odbija drop i otvori fajl u novom tabu
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          void handleFiles(e.dataTransfer.files)
        }}
      >
        <p>Prevuci fajl ovde ili</p>
        <label className="file-button">
          izaberi fajl
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            disabled={busy}
            onChange={(e) => {
              void handleFiles(e.target.files)
              //bez brisanja vrednosti, isti fajl drugi put ne emituje change
              e.target.value = ''
            }}
          />
        </label>
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="...ili zalepi tekst ovde"
        rows={5}
        disabled={busy}
      />
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Naslov (opciono)"
        disabled={busy}
      />
      <button type="button" onClick={() => void handleText()} disabled={busy || !text.trim()}>
        {busy ? 'Obradjujem...' : 'Dodaj tekst'}
      </button>

      {error && <p className="error">{error}</p>}
    </section>
  )
}
