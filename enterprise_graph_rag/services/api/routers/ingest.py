import shutil
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.worker.tasks import process_document_task
from services.api.schemas import IngestResponse
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from services.worker.tasks import process_document_task
from services.api.schemas import IngestResponse
from services.core.storage import StorageManager
from knowledge_engine.core.logging import logger

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

UPLOAD_DIR = "./data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=IngestResponse, status_code=202)
async def upload_document(file: UploadFile = File(...)):
    """
    Secure upload endpoint.
    """
    logger.info("ingest_request_received", filename=file.filename)
    
    try:
        # 1. Save Securely
        file_path = StorageManager.save_upload(file)
        
        # 2. Dispatch Async Task
        # Note: We pass the 'original' filename for metadata, but processing happens on the secure path
        task = process_document_task.delay(file_path, file.filename)
        
        return IngestResponse(
            task_id=task.id,
            status="accepted",
            message=f"File queued. Task ID: {task.id}"
        )
    except Exception as e:
        logger.error("upload_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Upload failed processing.")