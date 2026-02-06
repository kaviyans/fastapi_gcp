"""
FastAPI application for GCP Cloud Run deployment.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
import os

app = FastAPI(
    title="Cloud Run FastAPI Service",
    description="A lightweight FastAPI service deployed on GCP Cloud Run",
    version="1.0.0",
)

# CORS — allow all origins for demo; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------- Models ---------------

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    environment: str


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    quantity: int = 1


class ItemResponse(BaseModel):
    id: int
    item: Item
    created_at: str


# --------------- In-memory store ---------------

_items: dict[int, dict] = {}
_counter: int = 0


# --------------- Routes ---------------

@app.get("/", response_model=HealthResponse)
def root():
    """Health check / root endpoint — used by Cloud Run readiness probes."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "dev"),
    )


@app.get("/health", response_model=HealthResponse)
def health():
    """Explicit health-check endpoint."""
    return root()


@app.get("/items", response_model=list[ItemResponse])
def list_items():
    """List all items."""
    return [
        ItemResponse(id=item_id, item=Item(**data["item"]), created_at=data["created_at"])
        for item_id, data in _items.items()
    ]


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: Item):
    """Create a new item."""
    global _counter
    _counter += 1
    record = {
        "item": item.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _items[_counter] = record
    return ItemResponse(id=_counter, item=item, created_at=record["created_at"])


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    """Retrieve a single item by ID."""
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    data = _items[item_id]
    return ItemResponse(id=item_id, item=Item(**data["item"]), created_at=data["created_at"])


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    """Delete an item by ID."""
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    del _items[item_id]
