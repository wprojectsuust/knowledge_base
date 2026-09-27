from dotenv import load_dotenv

load_dotenv()

from src.api.app import app  # noqa: E402

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
