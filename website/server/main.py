from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Chess-LLM Arena API")

# Configure CORS for portfolio subdomain (and local dev)
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",
    # Add production domain later
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")  # type: ignore
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
