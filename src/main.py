from fastapi import FastAPI
from src.prompts import router as prompts_router

app = FastAPI()

# Include routers
app.include_router(prompts_router.router)


@app.get("/health")
async def health():
    return {"status": "UP"}
