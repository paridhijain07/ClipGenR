from typing import Any, List
from fastapi import APIRouter
from backend.app.services.caption.caption_engine import caption_engine

router = APIRouter()


@router.get("", response_model=List[dict])
def list_caption_presets() -> Any:
    """List available styled caption presets (Hormozi, Beast, Neon, Minimal)."""
    return caption_engine.list_presets()
