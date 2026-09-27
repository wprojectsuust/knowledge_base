from fastapi import FastAPI

from src.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="УУНиТ Knowledge Base")
    app.include_router(router)
    return app


app = create_app()
