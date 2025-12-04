import json
import redis
from celery.signals import worker_process_init
from services.worker.app import celery_app
from knowledge_engine.ingestion.loader import IngestionPipeline
from knowledge_engine.ingestion.cleaner import GraphCleaner
from knowledge_engine.core.logging import configure_logging, logger

pipeline = None
redis_client = None

@worker_process_init.connect
def init_worker(**kwargs):
    global pipeline, redis_client
    configure_logging()
    pipeline = IngestionPipeline()
    # Separate Redis connection for Pub/Sub
    redis_client = redis.from_url(celery_app.conf.broker_url)

def publish_progress(task_id: str, status: str, percent: int, msg: str):
    """Helper to publish real-time updates."""
    if redis_client:
        payload = json.dumps({
            "task_id": task_id,
            "status": status,
            "percent": percent,
            "message": msg
        })
        # Publish to channel: task_updates:{task_id}
        redis_client.publish(f"task_updates:{task_id}", payload)

@celery_app.task(bind=True, name="process_document_task", max_retries=3)
def process_document_task(self, file_path: str, original_filename: str):
    global pipeline
    if not pipeline: pipeline = IngestionPipeline()
    
    task_id = self.request.id
    logger.info("task_started", task_id=task_id)
    
    # Notify Start
    publish_progress(task_id, "processing", 10, "Starting ingestion pipeline...")

    try:
        # Loop for Async Execution
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        directory = os.path.dirname(file_path)
        
        # Notify Extraction
        publish_progress(task_id, "extracting", 30, "Extracting entities with LLM...")
        result = loop.run_until_complete(pipeline.process_directory_async(directory))
        
        # Notify Cleanup
        publish_progress(task_id, "cleaning", 80, "Optimizing Graph structure...")
        cleaner = GraphCleaner()
        cleaner.run_all()
        
        # Notify Done
        publish_progress(task_id, "completed", 100, "Ingestion finished successfully.")
        
        return {"status": "success", "meta": result}
        
    except Exception as e:
        publish_progress(task_id, "failed", 0, f"Error: {str(e)}")
        logger.error("task_failed", error=str(e))
        raise self.retry(exc=e, countdown=10)