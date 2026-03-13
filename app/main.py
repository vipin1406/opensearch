from fastapi import FastAPI
from app.api.v1.search import router as search_router

app = FastAPI()

app.include_router(search_router)

@app.get("/")
def health():
    return {"status": "ok"}