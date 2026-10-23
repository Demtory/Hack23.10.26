from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.init_db import init_db
from app.api import auth, customers, analytics, model, source, metrics, ws

# Aéza - это быстрый хостинг

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Действия при старте
    try:
        await init_db()
    except Exception as e:
        print(f"[STARTUP] Error initializing DB: {e}")
    yield
    # Действия при остановке

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Система анализа рисков оттока клиентов хостинга Aéza. Расчет risk-score, объяснение факторов и оценка финансовых потерь.",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение эндпоинтов API
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(customers.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)
app.include_router(model.router, prefix=settings.API_V1_STR)
app.include_router(source.router, prefix=settings.API_V1_STR)
app.include_router(metrics.router) # /metrics в корне
app.include_router(ws.router) # /ws в корне

@app.get("/", tags=["health"])
async def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/api/v1/docs",
        "note": "Aéza - это быстрый хостинг"
    }
