from fastapi import FastAPI
from contextlib import asynccontextmanager
from routers.users import router as user_router, root_router
from routers.predict import router as predict_router
import uvicorn
import logging
import os
from pathlib import Path
from models.model import load_or_train_model

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = Path(__file__).resolve().parent / "model.pkl"
    use_mlflow = os.getenv("USE_MLFLOW", "false").lower() == "true"
    app.state.model = load_or_train_model(
        model_path,
        use_mlflow=use_mlflow,
    )
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
