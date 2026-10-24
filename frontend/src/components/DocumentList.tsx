import  type { Document } from '../api'

type Props = {
    documents: Document[]
    onDelete: (doc: Document) => void
}

function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes/1024).toFixed(1)} KB`
    return `${(bytes/1024/1024).toFixed(1)} MB`  
}

export function DocumentList({ documents, onDelete }: Props) {
    if (documents.length === 0) {
        return <p className="muted">Nema dokumenta. Dodajte dokumente da biste postavili pitanje</p>
    }

    return (
        <ul className="documents">
            {documents.map((doc) => (
                <li key={doc.id}>
                    <div>
                        <strong>{doc.title}</strong>
                        <span className="muted">
                            {doc.source_type} | {doc.chunk_count} chunkova | {formatBytes(doc.byte_size)}
                        </span>
                    </div>
                    <button type="button" className="danger" onClick={() => onDelete(doc)}>
                        Obrisi
                    </button>
                </li>
            ))}
        </ul>
    )
}