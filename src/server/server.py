import asyncio
import datetime
import logging

from thermostat.radio_thermo_api_client import RadioThermoApiClient

from .dto_converter import DtoConverter
from .schedule_dto import ScheduleData
from .server_interface import ServerInterface
from .state_dto import TimeInfo

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class Server(ServerInterface):
    def __init__(self):
        self.thermostat = RadioThermoApiClient()


    async def get_thermostat_schedule(self):
        program = await self.thermostat.get_heating_program()
        return DtoConverter.thermostat_program_to_schedule(program)


    async def update_thermostat_schedule(self, schedule_data: ScheduleData):
        thermostat_data = DtoConverter.schedule_to_thermostat_program(schedule_data)
        return await self.thermostat.update_heating_program(thermostat_data)


    async def set_time(self, time_info: TimeInfo):
        thermostat_time = DtoConverter.server_time_to_thermostat(time_info)
        return await self.thermostat.set_time(thermostat_time)


    async def set_current_time(self):
        time_info = DtoConverter.get_time_info(datetime.now().astimezone())
        thermostat_time = DtoConverter.server_time_to_thermostat(time_info)
        return await self.thermostat.set_time(thermostat_time)


    async def get_state(self):
        state = await self.thermostat.get_state()
        server_dto = DtoConverter.thermostat_state_to_server(state)
        
        # If time is out of sync, attempt to sync it in the background
        if server_dto.time_status != "in sync":
            task = asyncio.create_task(self.set_time(server_dto.server_time))
            # Add error callback to log failures
            task.add_done_callback(
                lambda t: logger.warning("Failed to set thermostat time") if t.exception() else None
            )
        return server_dto



