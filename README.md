# ask-your-docs

Lokalna RAG aplikacija: ubaciš PDF, DOCX, Markdown ili zalepljen tekst, ona ga iscepa na komade
od ~800 znakova, vektorizuje ih preko OpenAI `text-embedding-3-small` i čuva u Postgresu sa
`pgvector` ekstenzijom. Na postavljeno pitanje kosinusnom pretragom nađe najbliže komade i
prosledi ih lokalnom Ollama modelu (`llama3.2:3b`), koji odgovor streamuje token po token uz
prikaz citiranih izvora — ceo stack radi u Docker Compose-u.

Pitanja i odgovori ne izlaze sa tvoje mašine. Jedino što ide u oblak je vektorizacija teksta.

---

## Kako radi

```
Browser :5173  ──►  web (Vite)  ──proxy /api──►  api (FastAPI)  ──►  db (Postgres + pgvector)
                                                      │
                                                      ├──►  Ollama na hostu  :11434
                                                      └──►  OpenAI API (embeddings)
```

**Upload:** fajl → izvlačenje teksta → cepanje na komade sa preklapanjem → vektorizacija (OpenAI,
grupe po 64) → upis dokumenta i svih komada u jednoj transakciji.

**Pitanje:** pitanje se vektorizuje istim modelom → SQL upit sa kosinusnom distancom vrati 5
najbližih komada → komadi idu Ollami kao kontekst → odgovor se streamuje nazad kao NDJSON.

## Stack

| Sloj | Tehnologija |
|---|---|
| Baza | Postgres 17 + pgvector (HNSW indeks) |
| Backend | Python 3.12, FastAPI, uvicorn, psycopg 3 |
| Embeddings | OpenAI `text-embedding-3-small`, 1536 dimenzija |
| LLM | Ollama + `llama3.2:3b`, lokalno |
| Frontend | React 19, TypeScript, Vite 8 |
| Pakovanje | Docker Compose |

Bez LangChaina — chunking, SQL za pretragu i HTTP pozivi su pisani ručno.

---

## Preduslovi

- **Docker Desktop** (ili Docker Engine + Compose)
- **Ollama** instalirana na hostu, sa povučenim modelom:
  ```
  ollama pull llama3.2:3b
  ```
- **`OLLAMA_HOST=0.0.0.0`** kao sistemska env varijabla, pa restart Ollame.
  Bez toga Ollama sluša samo na `127.0.0.1` i kontejner je ne vidi.
- **OpenAI API ključ** sa pristupom embeddings modelima.

> Ako ti na portu **5432** već radi lokalni Postgres, ne smeta — baza iz Compose-a se mapira na
> **5433** na hostu. Unutar Docker mreže i dalje koristi 5432.

## Podešavanje

Napravi `.env` u korenu projekta:

```env
# Postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=askyourdocs
# host "db" je ime servisa iz compose.yml, ne localhost
DATABASE_URL=postgresql://postgres:postgres@db:5432/askyourdocs

# Embeddings
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# LLM na hostu — mora http://, Ollama ne govori TLS
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:3b

# Retrieval
TOP_K=5
CHUNK_SIZE=800
CHUNK_OVERLAP=150
```

| Varijabla | Podrazumevano | Šta radi |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@db:5432/askyourdocs` | konekcija na bazu iz kontejnera |
| `OPENAI_API_KEY` | — | **obavezno**, bez njega upload ne radi |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | model za vektorizaciju |
| `EMBEDDING_DIM` | `1536` | mora da odgovara `vector(N)` u šemi |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | adresa Ollame sa stanovišta kontejnera |
| `OLLAMA_MODEL` | `llama3.2:3b` | model koji generiše odgovore |
| `TOP_K` | `5` | koliko komada ide u kontekst |
| `CHUNK_SIZE` | `800` | ciljna dužina komada u znakovima |
| `CHUNK_OVERLAP` | `150` | preklapanje; mora biti manje od pola `CHUNK_SIZE` |

## Pokretanje

```bash
docker compose up -d
```

Prvi put traje nekoliko minuta — gradi se backend image i instaliraju se npm paketi.

- UI: **http://localhost:5173**
- API: **http://localhost:8000**, dokumentacija na **/docs**
- Baza sa hosta: `localhost:5433`

Provera da je sve živo:

```bash
curl http://localhost:8000/api/health
# {"status":"ok","db":true}

docker compose exec api python -c "from app import llm; print(llm.is_available())"
# True
```

Gašenje:

```bash
docker compose down      # podaci ostaju u pgdata volumenu
docker compose down -v   # briše i bazu
```

---

## API

| Metoda | Putanja | Telo | Uspeh | Greške |
|---|---|---|---|---|
| `GET` | `/api/health` | — | 200 | — |
| `POST` | `/api/documents` | multipart, polje `file` | 201 | 413, 415, 422 |
| `POST` | `/api/documents/text` | `{"content": "...", "title": "..."}` | 201 | 422 |
| `GET` | `/api/documents` | — | 200 | — |
| `DELETE` | `/api/documents/{id}` | — | 204 | 404, 422 |
| `POST` | `/api/ask` | `{"question": "..."}` | 200 (stream) | 409, 422, 503 |

Podržani formati: `.pdf`, `.docx`, `.txt`, `.md`. Limit 10 MB po fajlu, 200 000 znakova za
zalepljen tekst.

### Kodovi grešaka

| Kod | Kad |
|---|---|
| 409 | pitanje postavljeno a baza je prazna |
| 413 | fajl veći od 10 MB |
| 415 | nepodržana ekstenzija |
| 422 | prazan ili nečitljiv sadržaj, neispravan UUID |
| 503 | Ollama ne odgovara |

### Stream na `/api/ask`

Odgovor je NDJSON — jedan JSON objekat po redu:

```
{"type":"sources","sources":[{"index":1,"title":"...","score":0.59,"preview":"..."}]}
{"type":"token","text":"Docker"}
{"type":"token","text":" Postgres"}
{"type":"done"}
```

Red `sources` izlazi prvi i tačno jedanput. `token` nula ili više puta. Ako generisanje pukne u
sredini, stiže `{"type":"error","message":"..."}`. Red `done` izlazi **uvek**, i posle greške —
pa klijent ima jedno pravilo: čitaj do `done`, i ako si video `error`, prikaži ga.

Primer:

```bash
curl -N -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Na kom portu je baza?"}'
```

---

## Struktura

```
backend/
  app/
    config.py        podešavanja iz .env
    db.py            connection pool, šema pri startu
    main.py          FastAPI aplikacija, lifespan, CORS
    extract.py       pdf/docx/txt/md → tekst
    chunking.py      tekst → komadi sa preklapanjem
    embeddings.py    komadi → vektori (OpenAI, batch 64)
    llm.py           Ollama, streaming odgovora
    routers/
      documents.py   upload, lista, brisanje
      ask.py         vektorska pretraga + stream
  database/init/
    001_schema.sql   tabele documents i chunks, HNSW indeks
frontend/
  src/
    api.ts           svi pozivi ka backendu, čitanje NDJSON streama
    App.tsx          stanje i raspored
    components/      AskPanel, UploadPanel, DocumentList
compose.yml          db, api, web
```

## Razvoj

Oba servisa imaju hot reload — backend kroz `uvicorn --reload`, frontend kroz Vite HMR. Izmena
fajla u editoru se odmah vidi, bez `rebuild`.

```bash
docker compose logs -f api     # logovi backenda
docker compose logs -f web     # logovi Vite-a
docker compose exec db psql -U postgres -d askyourdocs
```

> **Posle izmene `.env` treba recreate kontejnera.** Env varijable se ubacuju pri pravljenju
> kontejnera, a `--reload` gleda samo `.py` fajlove:
> ```
> docker compose up -d --force-recreate api
> ```

> **`docker ps` sa statusom `Up` ne znači da backend radi.** Uvicorn sa `--reload` ima roditeljski
> proces koji preživi pad deteta. Kad nešto ne odgovara, prvo pogledaj `docker compose logs api`.

Provera frontenda bez Dockera:

```bash
cd frontend
npm install
npm run build     # tsc + vite build, strožije od dev režima
```

## Poznata ograničenja

- **Nema praga relevantnosti** u pretrazi — `LIMIT TOP_K` uzima pet najboljih bez obzira na
  sličnost, pa sa mnogo dokumenata u kontekst ulazi i šum.
- **Tabele u `.docx` se ne čitaju** — obrađuju se samo pasusi.
- **Nema autentifikacije ni rate limita.** Namenjeno lokalnom pokretanju.
- **`llama3.2:3b` ne citira izvore pouzdano.** Zato se izvori prikazuju iz `sources` reda, a ne iz
  teksta odgovora.
- **Promena embedding modela zahteva praznu bazu** — stari i novi vektori nisu uporedivi, a
  `vector(N)` u šemi mora da odgovara novoj dimenziji.
