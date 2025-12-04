import os
from celery import Celery
from knowledge_engine.core.config import settings

# Initialize Celery
# Broker: Redis (for queue)
# Backend: Redis (to store results/status)
celery_app = Celery(
    "ingestion_worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=["services.worker.tasks"]
)

# Optimization: Enterprise Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Optimization: Prefetch multiplier 1 ensures worker doesn't hoard tasks
    worker_prefetch_multiplier=1,
    # Optimization: Acknowledge task only after completion (durability)
    task_acks_late=True,
    # Optimization: Route specific tasks to specific queues
    task_routes={
        "process_document_task": {"queue": "ingestion_queue"},
        "*": {"queue": "default"}
    },
    # Optimization: Global Rate Limit for ingestion (avoid 429s)
    task_annotations={
        "process_document_task": {"rate_limit": "10/m"} 
    }
)