from fastapi import FastAPI
from fastapi.responses import Response
from contextlib import asynccontextmanager
from routers.users import router as user_router, root_router
from routers.predict import router as predict_router
from routers.async_moderation import router as async_moderation_router
import uvicorn
import logging
import os
from pathlib import Path
from models.model import load_model, load_model_from_mlflow, train_and_save_model
from db.connection import DB_DSN, close_pg_pool, init_pg_pool
from db.migrate import apply_migrations
from clients.kafka import KafkaClient
from clients.redis import RedisClient
from storages.prediction_cache import PredictionCacheStorage
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from app.prometheus_middleware import PrometheusMiddleware
from app.sentry import init_sentry, report_exception

logging.basicConfig(level=logging.INFO)
init_sentry()

@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = Path(__file__).resolve().parent / "model.pkl"
    migrations_dir = Path(__file__).resolve().parent / "db"
    use_mlflow = os.getenv("USE_MLFLOW", "false").lower() == "true"
    disable_kafka = os.getenv("DISABLE_KAFKA", "false").lower() == "true"
    disable_redis = os.getenv("DISABLE_REDIS", "false").lower() == "true"
    kafka_client = None if disable_kafka else KafkaClient()
    redis_client = None if disable_redis else RedisClient()
    app.state.kafka_client = kafka_client
    app.state.redis_client = redis_client
    app.state.prediction_cache = None
    try:
        await init_pg_pool(DB_DSN)
        await apply_migrations(migrations_dir, DB_DSN)
    except Exception as exc:
        logging.exception("Failed to apply migrations: %s", exc)
        report_exception(exc)
        raise

    try:
        if redis_client is not None:
            try:
                await redis_client.start()
                app.state.prediction_cache = PredictionCacheStorage(redis_client.client)
            except Exception as exc:
                logging.exception("Failed to start Redis client: %s", exc)
                report_exception(exc)
                app.state.redis_client = None
                app.state.prediction_cache = None

        if kafka_client is not None:
            try:
                await kafka_client.start()
            except Exception as exc:
                logging.exception("Failed to stsrt Kafka client: %s", exc)
                report_exception(exc)
                app.state.kafka_client = None

        if use_mlflow:
            try:
                app.state.model = load_model_from_mlflow("moderation-model", "Production")
            except Exception:
                app.state.model = train_and_save_model(model_path, use_mlflow=True)
        elif model_path.exists():
            app.state.model = load_model(model_path)
        else:
            app.state.model = train_and_save_model(model_path)
    except Exception as exc:
        logging.exception("Failed to load model: %s", exc)
        report_exception(exc)
        app.state.model = None
    yield
    if redis_client is not None:
        await redis_client.stop()
    if kafka_client is not None:
        await kafka_client.stop()
    await close_pg_pool()

app = FastAPI(
    title="Moderation Model API",
    description="API for moderation model",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(PrometheusMiddleware)

@app.get("/")
async def root():
    return {'message': 'Hello World'}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

app.include_router(user_router, prefix='/users')
app.include_router(root_router)
app.include_router(predict_router)
app.include_router(async_moderation_router)



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
