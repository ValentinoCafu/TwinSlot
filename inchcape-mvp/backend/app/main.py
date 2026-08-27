from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import afinidad, ergonomia, ingesta, pipeline, recomendaciones, reglas, zonas
from app.core.config import CORS_ORIGINS
from app.core.db import init_db, seed_zonas_si_vacio


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_zonas_si_vacio()
    yield


app = FastAPI(
    title="Sombra digital -- Reslotting CD Aldeas",
    description="API que envuelve el pipeline de ingesta, reglas, scoring y optimización del MVP IMPULSA.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingesta.router)
app.include_router(zonas.router)
app.include_router(pipeline.router)
app.include_router(reglas.router)
app.include_router(ergonomia.router)
app.include_router(recomendaciones.router)
app.include_router(afinidad.router)


@app.get("/salud")
def salud() -> dict:
    return {"estado": "ok"}
