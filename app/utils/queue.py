from redis import Redis
from django.conf import settings

def enqueue_careplan_id(careplan_id: int) -> None:
    r = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    r.rpush(settings.CAREPLAN_QUEUE_KEY, str(careplan_id))
