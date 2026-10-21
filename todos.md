# ask-your-docs — todos

## 0. Setup na hostu (radi korisnik)
- [ ] Instaliran Ollama for Windows
- [ ] `ollama pull llama3.2:3b`
- [ ] Sistemski env var `OLLAMA_HOST=0.0.0.0` + restart Ollama
- [ ] `.env` napravljen iz `.env.example`, upisan `OPENAI_API_KEY`

## 1. Docker skelet i baza
- [ ] `.gitignore`, `git init`, initial commit na `main`
- [ ] `.env.example`
- [ ] `backend/database/init/001_schema.sql` (vector ext, documents, chunks, HNSW indeks)
- [ ] `compose.yml`: db (pgvector/pg17 + healthcheck + volume), api, web
- [ ] `docker compose up -d db` prolazi, `pg_isready` zdrav, tabele postoje

## 2. Backend
- [ ] `backend/Dockerfile` + `requirements.txt`
- [ ] `app/config.py`, `app/db.py` (pool + register_vector + idempotentna šema)
- [ ] `app/extract.py` (pdf / docx / txt / md)
- [ ] `app/chunking.py` (~800 znakova, 150 overlap)
- [ ] `app/embeddings.py` (OpenAI text-embedding-3-small, batch 64)
- [ ] `app/llm.py` (Ollama /api/chat streaming)
- [ ] `GET /api/health`
- [ ] `POST /api/documents` (upload) i `POST /api/documents/text`
- [ ] `GET /api/documents`, `DELETE /api/documents/{id}`
- [ ] `POST /api/ask` (vector search + NDJSON stream sa izvorima)
- [ ] Greške pokrivene: 415 nepoznat tip, 422 prazan tekst, 409 nema dokumenata, 503 Ollama offline

## 3. Frontend
- [ ] Vite + React + TS skelet (`package.json`, `vite.config.ts` sa `/api` proxy)
- [ ] `src/api.ts` (uključujući čitanje streama)
- [ ] `UploadPanel` (file + drag&drop + textarea)
- [ ] `DocumentList` (chunk count, brisanje sa potvrdom)
- [ ] `AskPanel` (token-po-token odgovor + panel izvora)
- [ ] `styles.css` (dark/light, dve kolone)

## 4. Verifikacija
- [ ] `/api/health` svi flagovi `true`
- [ ] Upload fajla preko curl-a kreira chunkove u bazi
- [ ] `/api/ask` streamuje odgovor sa citatima
- [ ] UI na `localhost:5173` radi ceo tok (upload → pitanje → citati → brisanje)
- [ ] `docker compose down && up` — podaci prežive
- [ ] `README.md` napisan
- [ ] Commit sa svim radnim kodom
