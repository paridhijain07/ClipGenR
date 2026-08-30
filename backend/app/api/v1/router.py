from fastapi import APIRouter
from backend.app.api.v1.endpoints import auth, clips, presets, videos

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(videos.router, prefix="/videos", tags=["Videos & Pipeline"])
api_router.include_router(clips.router, prefix="/clips", tags=["Clips & Studio"])
api_router.include_router(presets.router, prefix="/presets", tags=["Caption Presets"])
