from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("neo_reels", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_default_queue="default")

celery_app.autodiscover_tasks(["app.tasks"])
