import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from config.settings import settings

from .schedule_dto import ScheduleData
from .server_interface import ServerInterface
from .state_dto import StateDTO, TimeInfo

logger = logging.getLogger(__name__)

class CacheItem:
    def __init__(self, data):
        self.data = data
        self.expireTime = datetime.now().astimezone() + timedelta(seconds=settings.cache_ttl_seconds)

    def is_expired(self) -> bool:
        return self.expireTime < datetime.now().astimezone()
        

class CachingSequentialServer(ServerInterface):
    def __init__(self, server: ServerInterface, refresh_interval: float = 60.0):
        if refresh_interval <= 0:
            raise ValueError("refresh_interval must be greater than zero")

        self.server = server
        self._refresh_interval = refresh_interval
        self._lock = asyncio.Lock()
        self._cached_schedule: CacheItem | None = None
        self._cached_state: CacheItem | None = None
        self._refresh_task: asyncio.Task[None] | None = None

    async def start_background_refresh(self) -> None:
        if self._refresh_task is None or self._refresh_task.done():
            logger.info("Starting background refresh task")
            self._refresh_task = asyncio.create_task(self._refresh_cache_loop())

    async def stop_background_refresh(self) -> None:
        task = self._refresh_task
        self._refresh_task = None
        if task is not None:
            logger.info("Stopping background refresh task")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _refresh_cache_loop(self) -> None:
        while True:
            try:
                await self.get_thermostat_schedule(checkExpired = True)
                await self.get_state(checkExpired = True)
            except asyncio.CancelledError:
                logger.info("Background refresh task cancelled while making REST call")
                raise
            except Exception:
                logger.exception("Failed to refresh thermostat cache")

            try:
                await asyncio.sleep(settings.cache_ttl_seconds / 10)
            except asyncio.CancelledError:
                logger.info("Background refresh task cancelled while sleeping")
                raise

    async def get_thermostat_schedule(self, checkExpired: bool = False) -> ScheduleData:
        if self._cached_schedule is not None and (not self._cached_schedule.is_expired() or not checkExpired):
            return self._cached_schedule.data
        
        async with self._lock:
            if self._cached_schedule is None or self._cached_schedule.is_expired():
                self._cached_schedule = CacheItem(await self.server.get_thermostat_schedule())

        return self._cached_schedule.data

    async def update_thermostat_schedule(self, schedule_data: ScheduleData) -> Any:
        async with self._lock:
            result = await self.server.update_thermostat_schedule(schedule_data)
            self._cached_schedule = CacheItem(schedule_data)
            return result

    async def set_time(self, time_info: TimeInfo) -> Any:
        async with self._lock:
            return await self.server.set_time(time_info)


    async def set_current_time(self) -> Any:
        async with self._lock:
            return await self.server.set_current_time()
        

    async def get_state(self, checkExpired: bool = False) -> StateDTO:
        if self._cached_state is not None and (not self._cached_state.is_expired() or not checkExpired):
            return self._cached_state.data
        
        async with self._lock:
            if self._cached_state is None or self._cached_state.is_expired():
                self._cached_state = CacheItem(await self.server.get_state())
                self.sync_time_if_needed()

        return self._cached_state.data

    def sync_time_if_needed(self) -> Any:
        if self._cached_state.data.time_status != "in sync":
            task = asyncio.create_task(self.set_current_time())
            # Add error callback to log failures
            task.add_done_callback(
                lambda t: logger.warning("Failed to set thermostat time") if t.exception() else None
            )