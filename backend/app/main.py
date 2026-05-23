import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.database import Base, engine
from app.routers import auth, projects, labels, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear tablas al iniciar
    Base.metadata.create_all(bind=engine)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Registrar routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(labels.router)
app.include_router(reports.router)

# Montar directorio de uploads para servir imágenes (se crea en lifespan)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.get("/api/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}
