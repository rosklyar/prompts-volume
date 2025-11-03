from fastapi import FastAPI
from src.routers import prompts

app = FastAPI()

# Include routers
app.include_router(prompts.router)


@app.get("/health")
async def health():
    return {"status": "UP"}
