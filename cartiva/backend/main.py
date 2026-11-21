from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from cartiva.backend.catalog import router as catalog_router
from cartiva.backend.cart import router as cart_router

STOREFRONT_DIR = Path(__file__).resolve().parents[1] / "storefront"

app = FastAPI(
    title="Cartiva API",
    description="Backend API for the Cartiva fashion application.",
    version="0.1.0",
)

app.include_router(catalog_router)

app.include_router(cart_router)

# The storefront is a static page that calls the API above from the browser.
app.mount("/shop", StaticFiles(directory=STOREFRONT_DIR, html=True), name="shop")


@app.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    """Send visitors to the storefront."""
    return RedirectResponse(url="/shop/")


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Confirm that the Cartiva API is responding."""
    return {
        "status": "ok",
        "application_id": "cartiva",
        "version": app.version,
    }
