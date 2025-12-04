import os
import magic # pip install python-magic
import aiofiles
from fastapi import UploadFile, HTTPException
import uuid
import aiofiles # Async File IO
from knowledge_engine.core.logging import logger

class StorageManager:
    UPLOAD_DIR = "./data/uploads"
    CHUNK_SIZE = 1024 * 64 # 64KB chunks
    
    # Allowed Mime Types
    ALLOWED_TYPES = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt"
    }

    @classmethod
    async def save_upload_stream(cls, file: UploadFile) -> str:
        """
        Optimization: Memory-safe stream writing for large files.
        """
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        
        header = await file.read(2048)
        await file.seek(0) # Reset cursor to start
        mime = magic.from_buffer(header, mime=True)
        
        if mime not in cls.ALLOWED_TYPES:
            # Fallback: Sometimes magic misidentifies text, so we permit if extension matches
            # but for binary formats (PDF/DOCX) we are strict.
            if not (mime == "text/plain" and file.filename.endswith(".txt")):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Security Error: File type '{mime}' not allowed. Detected content does not match extension."
                )
       
        file_ext = os.path.splitext(file.filename)[1]
        unique_name = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(cls.UPLOAD_DIR, unique_name)
        
        try:
            # Open file asynchronously
            async with aiofiles.open(file_path, 'wb') as out_file:
                while content := await file.read(cls.CHUNK_SIZE):
                    await out_file.write(content)
            
            logger.info("file_streamed_to_disk", path=file_path)
            return file_path
        except Exception as e:
            logger.error("file_save_failed", error=str(e))
            raise e