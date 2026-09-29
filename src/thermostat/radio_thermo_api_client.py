import json
import logging

import httpx

from config.settings import settings

from .radio_thermo_program_dto import RadioThermoProgramDto
from .radio_thermo_state_dto import RadioThermoStateDto, RadioThermoTimeInfoDto

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class RadioThermoApiClient:
    def __init__(self):
        self.tstat_url = settings.thermostat_url + "tstat"
        self.heating_program_url = self.tstat_url + "/program/heat"
        self.time_url = self.tstat_url + "/time"

    async def get_heating_program(self) -> RadioThermoProgramDto:
        program = await self._get(self.heating_program_url)
        return RadioThermoProgramDto.model_validate(program)  


    async def update_heating_program(self, program_data: RadioThermoProgramDto):
        return await self._post(self.heating_program_url, program_data.model_dump())


    async def set_time(self, time_data : RadioThermoTimeInfoDto | dict):
        if isinstance(time_data, RadioThermoTimeInfoDto):
            data = time_data.model_dump()
        else:
            data = time_data
        return await self._post(self.time_url, data)

    
    async def get_state(self) -> RadioThermoStateDto:
        raw_data = await self._get(self.tstat_url)
        return RadioThermoStateDto.model_validate(raw_data)
            
            
    async def _get(self, url: str):
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            raw_data = response.json()
            logger.info(f"Received thermostat data from GET {url}: {json.dumps(raw_data, indent=2)}")
            return raw_data
        
            
    async def _post(self, url: str, data):
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
            raw_data = response.json()
            logger.info(f"Received thermostat data from POST {url}: {json.dumps(raw_data, indent=2)}")
            return raw_data
