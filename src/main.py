from fastapi import FastAPI
from src.topics import router as topics_router
from src.prompts import router as prompts_router

app = FastAPI()

# Include routers
app.include_router(topics_router.router)
app.include_router(prompts_router.router)


@app.get("/health")
async def health():
    return {"status": "UP"}
