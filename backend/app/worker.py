from backend.app.core.database import SessionLocal
from backend.app.core.logging import logger
from backend.app.services.pipeline.orchestrator import pipeline_orchestrator


def run_pipeline_task(video_id: str, job_id: str = None) -> bool:
    """
    Background worker entrypoint executing the pipeline in an isolated DB session.
    """
    logger.info("Starting async pipeline worker task", video_id=video_id, job_id=job_id)
    db = SessionLocal()
    try:
        success = pipeline_orchestrator.process_video(db=db, video_id=video_id, job_id=job_id)
        return success
    except Exception as e:
        logger.error("Unhandled exception in pipeline worker task", video_id=video_id, error=str(e))
        return False
    finally:
        db.close()
