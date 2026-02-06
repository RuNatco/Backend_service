from fastapi import FastAPI
from contextlib import asynccontextmanager
from routers.users import router as user_router, root_router
from routers.predict import router as predict_router
import uvicorn
import logging
import os
from pathlib import Path
from models.model import load_model, load_model_from_mlflow, train_and_save_model
from db.connection import DB_DSN
from db.migrate import apply_migrations

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = Path(__file__).resolve().parent / "model.pkl"
    migrations_dir = Path(__file__).resolve().parent / "db"
    use_mlflow = os.getenv("USE_MLFLOW", "false").lower() == "true"
    try:
        apply_migrations(migrations_dir, DB_DSN)
        if use_mlflow:
            try:
                app.state.model = load_model_from_mlflow("moderation-model", "Production")
                logging.info("Model loaded from MLflow registry")
            except Exception:
                app.state.model = train_and_save_model(model_path, use_mlflow=True)
                logging.info("Model trained and registered in MLflow")
        elif model_path.exists():
            app.state.model = load_model(model_path)
            logging.info("Model loaded from local file: %s", model_path)
        else:
            app.state.model = train_and_save_model(model_path)
            logging.info("Model trained and saved to local file: %s", model_path)
    except Exception as exc:
        logging.exception("Failed to load model: %s", exc)
        app.state.model = None
    yield

app = FastAPI(
    title="Moderation Model API",
    description="API for moderation model",
    version="0.1.0",
    lifespan=lifespan,
)

@app.get("/")
async def root():
    return {'message': 'Hello World'}

app.include_router(user_router, prefix='/users')
app.include_router(root_router)
app.include_router(predict_router)



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
