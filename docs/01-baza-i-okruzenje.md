# Baza i okruženje — kako ovo radi i zašto

Beleške uz Fazu 1 projekta ask-your-docs. Zapisano 2026-10-20.

Konkretan nalaz na ovoj mašini: **na portu 5432 već sluša lokalni Postgres** (proces `postgres`, PID 6836). Zato Docker bazu mapiramo na 5433 — detalji u sekciji 4.

---

## 1. Docker Postgres je kompletno nova, odvojena baza

Docker image pravi **potpuno novog korisnika**. Ne kuca se postojeći pgAdmin username.

Zamisli to kao da si kupio drugi računar, instalirao Postgres na njega i stavio ga pod stol. Nema nikakve veze sa lokalnom instalacijom — druge binarije, drugi data direktorijum, drugi korisnici, druge baze. Jedino što dele je port opseg, i tu nastaje konflikt.

Kad `postgres` image startuje **prvi put sa praznim data direktorijumom**, njegov entrypoint skript:

1. pokrene `initdb` i napravi prazan Postgres cluster,
2. napravi superuser-a sa imenom iz `POSTGRES_USER` i šifrom iz `POSTGRES_PASSWORD`,
3. napravi bazu sa imenom iz `POSTGRES_DB`,
4. izvrši svaki `.sql` i `.sh` fajl iz `/docker-entrypoint-initdb.d/` po abecedi (zato `001_` prefiks),
5. restartuje server "za pravo" i počne da sluša.

Dakle `POSTGRES_USER=postgres` ne znači „koristi postojećeg postgres korisnika" — znači „**napravi** korisnika koji se zove postgres". Može slobodno `POSTGRES_USER=dimitrije` i `POSTGRES_PASSWORD=nekasifra123`; to onda postaje superuser te baze. Samo mora da se poklapa sa `DATABASE_URL`.

**Najvažnija zamka:** koraci 1-4 se izvršavaju **samo kad je volumen prazan**. Ako kasnije promeniš šifru u `.env` i uradiš `docker compose up`, ništa se neće promeniti — stara šifra i dalje važi, jer Postgres vidi već inicijalizovan data direktorijum i samo ga pokrene. Da se to resetuje, mora `docker compose down -v` (briše volumen, **briše i sve podatke**). Isto važi i za `001_schema.sql` — zato ga pozivamo i iz backenda pri startu, pa je pisan idempotentno.

---

## 2. Šta znači svaka varijabla u `.env`

```
POSTGRES_USER=postgres          # korisnik koji se KREIRA u kontejneru
POSTGRES_PASSWORD=postgres      # njegova sifra
POSTGRES_DB=askyourdocs         # baza koja se KREIRA
```

Ove tri čita **sam Postgres image**. U compose-u ih prosleđujemo servisu `db`.

```
DATABASE_URL=postgresql://postgres:postgres@db:5432/askyourdocs
```

Ovu čita **Python kod**. Format: `postgresql://korisnik:sifra@host:port/baza`. Obrati pažnju na host — piše **`db`**, a ne `localhost`. To je ime servisa iz `compose.yml`; Docker ima interni DNS, pa unutar compose mreže `db` rezolvuje u IP tog kontejnera. Iz `api` kontejnera, `localhost` je on sam, pa bi `localhost:5432` značilo „traži Postgres u mom sopstvenom kontejneru" — klasična greška početnika u Docker-u.

```
OPENAI_API_KEY=                 # za embeddings; ovo je i razlog sto .env ide u .gitignore
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536              # informativno + za proveru u kodu; u SQL-u je zakucano vector(1536)
```

```
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:3b
```

`host.docker.internal` je specijalno ime koje znači „**moj Windows host, gledano iz kontejnera**". Ollama radi na hostu (da koristi GPU), a backend u kontejneru, pa mu treba ta adresa. Zbog toga ide i `extra_hosts: ["host.docker.internal:host-gateway"]` u compose — na Docker Desktop-u često radi i bez toga, ali sa tim je eksplicitno i prenosivo.

```
TOP_K=5                         # koliko najslicnijih chunkova se salje modelu kao kontekst
CHUNK_SIZE=800                  # ciljna duzina chunka u znakovima
CHUNK_OVERLAP=150               # koliko se susedni chunkovi preklapaju
```

---

## 3. Ideja šeme — zašto dve tabele

Suština RAG-a: LLM ne može da „pročita" ceo PDF od 80 strana na svako pitanje (ne staje u kontekst, košta, i kvalitet pada). Zato dokument isečeš na pasuse, svaki pretvoriš u vektor, i na pitanje dovučeš samo 5 pasusa koji su po značenju najbliži pitanju.

**`documents`** = metapodaci o fajlu, jedan red po uploadu. Ovo je ono što korisnik vidi u listi i briše.

**`chunks`** = stvarni sadržaj, isečen na delove. Jedan dokument → mnogo chunkova:

- `content` — tekst pasusa, da može da se prikaže kao citat i pošalje modelu.
- `embedding vector(1536)` — isti taj tekst pretvoren u 1536 brojeva. Tekstovi sličnog značenja daju vektore koji su blizu u prostoru, i to je cela magija: „kako se pokreće projekat" i „pokretanje aplikacije" nemaju zajedničku reč, ali imaju blizak vektor. Zato vektorska pretraga nalazi ono što `LIKE '%...%'` nikad ne bi.
- `ordinal` — redni broj chunka unutar dokumenta, da može da se rekonstruiše redosled i da se kaže „ovo je 3. deo fajla".
- `ON DELETE CASCADE` — brisanjem dokumenta nestaju i svi njegovi chunkovi. Bez toga bi u pretrazi iskakali citati iz fajla koji više ne postoji.

Upit koji će raditi `/api/ask` svodi se na ovo:

```sql
SELECT d.title, c.content,
       1 - (c.embedding <=> %(q)s::vector) AS similarity
FROM chunks c
JOIN documents d ON d.id = c.document_id
ORDER BY c.embedding <=> %(q)s::vector
LIMIT 5;
```

`<=>` je pgvector operator za kosinusnu distancu (0 = identično, 2 = suprotno), pa je `1 - distanca` sličnost koja se lepo prikazuje kao procenat. Ključno: operator u `ORDER BY` **mora** da odgovara klasi indeksa (`vector_cosine_ops`). Ako napišeš indeks za kosinus a sortiraš po `<->` (L2), Postgres će tiho preskočiti indeks i raditi full scan — radi, ali sve sporije kako baza raste, i nikad ne javi grešku.

Zašto HNSW a ne IVFFlat: HNSW ne traži da tabela već ima podatke pri kreiranju indeksa (IVFFlat traži, jer mora da izračuna centroide), što je zlato kad počinješ od prazne baze.

---

## 4. Kako se baza pokreće i kako je gledaš iz pgAdmin-a

```powershell
docker compose up -d db          # samo baza
docker compose logs -f db        # pratis dok ne napise "database system is ready to accept connections"
docker compose exec db psql -U postgres -d askyourdocs -c "\dt"
```

Dve adrese za **istu** bazu:

| Odakle | Host | Port |
|---|---|---|
| iz `api` kontejnera (Python) | `db` | 5432 |
| sa Windows-a (pgAdmin, DBeaver) | `localhost` | mapirani port |

Pošto lokalni Postgres već drži 5432, u compose-u mapiramo na 5433:

```yaml
ports:
  - "5433:5432"     # levo = Windows, desno = u kontejneru
```

Levi broj je slobodan izbor, desni je fiksan jer Postgres unutra sluša 5432. `DATABASE_URL` ostaje `db:5432` — to je interna komunikacija, nje se mapiranje ne tiče.

U pgAdmin-u se onda dodaje **novi server**: host `localhost`, port `5433`, username/password/database tačno kako je u `.env`. Videćeš ga paralelno sa lokalnom bazom, kao dva odvojena servera — što i jesu.

---

## 5. Sledeći korak

`backend/database/init/001_schema.sql` — sadržaj po redu:

1. `CREATE EXTENSION IF NOT EXISTS vector;` — bez ovoga tip `vector` ne postoji.
2. `CREATE EXTENSION IF NOT EXISTS pgcrypto;` — daje `gen_random_uuid()` za default id.
3. Tabela `documents`: `id uuid PK DEFAULT gen_random_uuid()`, `title text`, `source_type text`, `byte_size integer`, `chunk_count integer`, `created_at timestamptz DEFAULT now()`.
4. Tabela `chunks`: `id bigserial PK`, `document_id uuid REFERENCES documents(id) ON DELETE CASCADE`, `ordinal integer`, `content text`, `embedding vector(1536)`.
5. Dva indeksa: običan na `chunks(document_id)` i vektorski `USING hnsw (embedding vector_cosine_ops)`.

Sve pisati kao `IF NOT EXISTS` — vidi zamku u sekciji 1.

Posle toga ide `compose.yml` (servisi `db`, `api`, `web`).
