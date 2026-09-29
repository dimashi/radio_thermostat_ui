from fastapi import APIRouter

from server.caching_sequential_server import CachingSequentialServer
from server.schedule_dto import ScheduleData
from server.server import Server
from server.server_interface import ServerInterface

router = APIRouter(prefix="/api", tags=["Schedule API"])
server: ServerInterface = CachingSequentialServer(Server())


@router.get("/schedule")
async def get_schedule():
    return await server.get_thermostat_schedule()


@router.put("/schedule")
async def update_schedule(schedule: ScheduleData):
    return await server.update_thermostat_schedule(schedule)


@router.get("/state")
async def get_state():
    return await server.get_state()


