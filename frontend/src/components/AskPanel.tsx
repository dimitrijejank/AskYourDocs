import { useState } from 'react'
import { ask, type Source } from '../api'

type Props = {
    disabled: boolean
}

export function AskPanel({ disabled }: Props) {
    const [question, setQuestion ] = useState('')
    const [answer, setAnswer ] = useState('')
    const [sources, setSources ] = useState<Source[]>([])
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState<string | null>(null)

    async function handleAsk() {
        const q = question.trim()
        if (!q) return

        setBusy(true)
        setError(null)
        setAnswer('')
        setSources([])

        try {
            await ask(q, {
                sources: setSources,
                token: (text) => setAnswer((prev) => prev + text),
                error: setError
            })
        } catch (err) {
            setError((err as Error).message)
        } finally {
            setBusy(false)
        }
    }
    return (
        <section className='panel'>
            <h2>Postavite pitanje:</h2>
            <textarea value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder='Unesite pitanje ovde...'
                rows={3}
                disabled={busy || disabled}
            />
            <button type='button' onClick={() => void handleAsk()}
                disabled={busy || disabled || !question.trim()}
            >
                {busy ? 'Odgovaram...' : 'Pitaj'}
            </button>

            {disabled && <p className='muted'>Dodajte dokument da biste mogli da postavite pitanje.</p>}
            {error && <p className='error'>{error}</p>}

            {answer && (
                <article className='answer'>
                    {answer}
                    {busy && <span className='caret'/>}
                </article>
            )}

            {sources.length > 0 && (
                <details className='sources' open>
                    <summary>Izvori ({sources.length})</summary>
                    <ol>
                        {sources.map((s) => (
                            <li key={s.index}>
                                <strong>{s.title}</strong>{' '}
                                <span className='muted'>
                                    chunk {s.ordinal} | slicnost {(s.score * 100).toFixed(0)}%
                                </span>
                                <p className='muted'>{s.preview}</p>
                            </li>
                        ))}
                    </ol>
                </details>
            )}
        </section>
    )
}