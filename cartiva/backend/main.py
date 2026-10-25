from fastapi import FastAPI
from cartiva.backend.catalog import router as catalog_router
from cartiva.backend.cart import router as cart_router

app = FastAPI(
    title="Cartiva API",
    description="Backend API for the Cartiva fashion application.",
    version="0.1.0",
)

app.include_router(catalog_router)

app.include_router(cart_router)

@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Confirm that the Cartiva API is responding."""
    return {
        "status": "ok",
        "application_id": "cartiva",
        "version": app.version,
    }