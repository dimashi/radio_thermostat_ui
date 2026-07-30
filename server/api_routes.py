import time

from cashews import cache
from cashews.key import get_cache_key, get_cache_key_template
from fastapi import APIRouter
from schedule_dto import ScheduleData

# from state_dto import StateDTO, TimeInfo
from server import Server

# Import your models (TimeSlot, ScheduleData, etc.) here

router = APIRouter(prefix="/api", tags=["Schedule API"])
server: Server = Server()

CACHE_KEY_SCHEDULE = "schedule"
cache.setup("mem://")


class TrafficMonitor:
    def __init__(self):
        self.last_request_time = time.time()
        self.ema_interval = 1.0  # Exponential Moving Average (seconds) between requests

    def record_hit(self):
        now = time.time()
        # Calculate how long it's been since the LAST hit
        current_interval = now - self.last_request_time
        
        # Update our average (EMA)
        # 0.1 weight means it takes about 10 requests to fully pivot to a new speed
        self.ema_interval = (0.9 * self.ema_interval) + (0.1 * current_interval)
        print(f"Updated EMA interval: {self.ema_interval:.2f} seconds, ttl: {self.get_dynamic_ttl():.2f} seconds")
        self.last_request_time = now

    def get_dynamic_ttl(self):
        # High traffic (small interval) = Short TTL
        # Low traffic (large interval) = Long TTL
        # Example: TTL is 60x the average interval
        return int(min(max(self.ema_interval * 60, 30), 3600))

monitor = TrafficMonitor()

def get_monitor():
    return monitor


@router.get("/schedule")
@cache.early(ttl = lambda: monitor.get_dynamic_ttl(), early_ttl = 10)
async def get_schedule():
    return await server.get_thermostat_schedule()

def get_schedule_key():
    # magic "v2" comes from line 56 or early.py.
    key_template = get_cache_key_template(get_schedule, prefix="early:v2")
    return get_cache_key(get_schedule, key_template)


@router.put("/schedule")
async def update_schedule(schedule: ScheduleData):
    result = await server.update_thermostat_schedule(schedule)
    cache_key = get_schedule_key()
    cached_value = await cache.get(cache_key)
    # Maintain tuple structure: [first_element, schedule]
    first_elem = cached_value[0] if cached_value and len(cached_value) > 0 else None
    await cache.set(cache_key, [first_elem, schedule], ttl=monitor.get_dynamic_ttl())    
    return result

@router.get("/state")
async def get_state():
    """Get current thermostat state as StateDTO"""
    state = await server.get_state()
    # current_time = time.localtime()
    return state


@router.get("/cache-debug")
async def debug_cache():
    # Use the EXACT same key variable you used in the other methods
    key = get_schedule_key()
    val = await cache.get_raw(key)
    return {
        "key_used": key,
        "value_in_cache": val,
        "type": str(type(val))
    }

