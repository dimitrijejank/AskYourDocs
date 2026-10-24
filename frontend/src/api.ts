export type Document = {
    id: string
    title: string
    source_type: string
    byte_size: number
    chunk_count: number
    created_at: string
}

export type Source = {
    index: number
    document_id: string
    title: string
    ordinal: number
    score: number
    preview: string
}

type StreamRow =
    | { type: 'sources'; sources: Source[] }
    | { type: 'token'; text: string }
    | { type: 'error'; message: string }
    | { type: 'done' }

async function request<T>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(url,init)

    if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail ?? `HTTP ${response.status}`)
    }

    return response.status === 204 ? (undefined as T) : response.json()
}

export function listDocuments(): Promise<Document[]> {
    return request('/api/documents')
}

export function uploadDocument(file: File): Promise<Document> {
    const form = new FormData()
    form.append('file', file)
    return request('/api/documents', { method: 'POST', body: form })
}

export function createTextDocument(content: string, title?: string): Promise<Document> {
    return request('/api/documents/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(title ? { content, title } : { content }),
    })
}

export function deleteDocument(id: string): Promise<void> {
    return request(`/api/documents/${id}`, { method: 'DELETE' })
}

export async function ask(
    question: string,
    on: {
        sources: (sources: Source[]) => void
        token: (text: string) => void
        error: (message: string) => void
    },
): Promise<void> {
    const response = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
    })

    if(!response.ok || !response.body) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail ?? `HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while(true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        let newline: number
        while ((newline = buffer.indexOf('\n')) !== -1) {
            const line = buffer.slice(0, newline).trim()
            buffer = buffer.slice(newline + 1)
            if (!line) continue

            const row: StreamRow = JSON.parse(line)
            if (row.type === 'sources') on.sources(row.sources)
            else if (row.type === 'token') on.token(row.text)
            else if (row.type === 'error') on.error(row.message)
        }
    }
}
