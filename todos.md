# ask-your-docs — todos

## 0. Setup na hostu (radi korisnik)
- [x] Instaliran Ollama for Windows
- [x] `ollama pull llama3.2:3b`
- [x] Sistemski env var `OLLAMA_HOST=0.0.0.0` + restart Ollama
- [x] `.env` napravljen iz `.env.example`, upisan `OPENAI_API_KEY`
- [ ] **`.env`: `OLLAMA_URL` na `http://host.docker.internal:11434`** — sada je `https://`, pa `/api/ask` vraća 503 (Ollama ne govori TLS)

## 1. Docker skelet i baza
- [x] `.gitignore`, `git init`, initial commit na `main`
- [x] `.env.example`
- [x] `backend/database/init/001_schema.sql` (vector ext, documents, chunks, HNSW indeks)
- [x] `compose.yml`: db (pgvector/pg17 + healthcheck + volume), api, web
- [x] `docker compose up -d db` prolazi, `pg_isready` zdrav, tabele postoje
- [ ] Commitovati premeštaj Dockerfile-a: `backend/Dockerfile`, `requirements.txt`, `.dockerignore` su untracked, a brisanje root `Dockerfile`-a nije stage-ovano

## 2. Backend
- [x] `backend/Dockerfile` + `requirements.txt`
- [x] `app/config.py`, `app/db.py` (pool + register_vector + idempotentna šema)
- [x] `app/extract.py` (pdf / docx / txt / md)
- [x] `app/chunking.py` (~800 znakova, 150 overlap, prelom na pasusu/rečenici)
- [x] `app/embeddings.py` (OpenAI text-embedding-3-small, batch 64)
- [x] `app/llm.py` (Ollama /api/chat streaming + `is_available()`)
- [x] `GET /api/health`
- [x] `POST /api/documents` (upload) i `POST /api/documents/text`
- [x] `GET /api/documents`, `DELETE /api/documents/{id}` (CASCADE briše chunkove)
- [x] `POST /api/ask` (vector search + NDJSON stream sa izvorima)
- [x] Greške pokrivene: 415 nepoznat tip, 422 prazan tekst/pitanje, 409 nema dokumenata, 503 Ollama offline — 415/422/503 provereni uživo, 409 ostaje da se proveri na praznoj bazi

## 3. Frontend
- [ ] Vite + React + TS skelet (`package.json`, `vite.config.ts` sa `/api` proxy)
- [ ] `src/api.ts` (uključujući čitanje NDJSON streama: `sources` → `token`* → `done`)
- [ ] `UploadPanel` (file + drag&drop + textarea)
- [ ] `DocumentList` (chunk count, brisanje sa potvrdom)
- [ ] `AskPanel` (token-po-token odgovor + panel izvora)
- [ ] `styles.css` (dark/light, dve kolone)

## 4. Verifikacija
- [x] `/api/health` svi flagovi `true`
- [x] Upload fajla preko curl-a kreira chunkove u bazi (`chunk_count` = stvarni broj redova, `vector_dims` 1536)
- [ ] `/api/ask` streamuje odgovor sa citatima — tok potvrđen uz privremeno pregažen `OLLAMA_URL`; čeka `.env` fix da prođe kroz endpoint
- [ ] UI na `localhost:5173` radi ceo tok (upload → pitanje → citati → brisanje)
- [x] `docker compose down && up` — podaci prežive (`pgdata` volumen)
- [ ] `README.md` napisan
- [ ] Commit sa svim radnim kodom
- [ ] Test sa pravim PDF-om i DOCX-om — do sada su probani samo `.md` i zalepljen tekst, pa `_read_pdf` i `_read_docx` grane nisu izvršene

## 5. Kasnije, nije blokirajuće
- [ ] Prag relevantnosti u `_search` — sada `LIMIT top_k` uzima i izvode sa skorom 0.27, pa šum ulazi u kontekst
- [ ] Limit veličine upload fajla u ruteru (trenutno ceo fajl ide u memoriju)
- [ ] Tabele u `.docx` (`document.tables`) — sada se čitaju samo pasusi
- [ ] Osvežiti graphify graf (`/graphify . --update`) — ne zna za `extract`, `chunking`, `embeddings`, `routers/`
