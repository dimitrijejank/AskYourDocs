from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .db import close_db, init_db, pool
from .routers import ask, documents

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    close_db()

app = FastAPI(title="ask-your-docs", lifespan=lifespan)
app.include_router(documents.router, prefix="/api")
app.include_router(ask.router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/api/health")
#Moraju sinhroni pozivi zbog pool-a da ne bi async zaledio ceo event loop
def healt():
    with pool.connection() as conn:
        db_ok = conn.execute("SELECT 1").fetchone()[0] == 1
    return {"status": "ok" if db_ok else "degraded",
            "db": db_ok}