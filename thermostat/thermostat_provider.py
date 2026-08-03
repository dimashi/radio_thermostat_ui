import json
import logging

import httpx
from fastapi import HTTPException

# from state_dto import StateDTO, TimeInfo

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class ThermostatProvider:
    def __init__(self):
        self.thermostat_url = "http://thermostat-22-33-6A/"
        self.schedule_url = self.thermostat_url + "tstat/program/heat"

    async def get_thermostat_schedule(self):
    
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(self.schedule_url)
                response.raise_for_status()
                schedule = response.json()
                logger.info(f"Received data from thermostat: {json.dumps(schedule, indent=2)}")
                return schedule
            except httpx.HTTPStatusError as exc:
                # exc.response.status_code is the code returned by the thermostat (e.g., 401, 404, 500)
                tstat_code = exc.response.status_code
                raise HTTPException(
                    status_code=502, 
                    detail=f"Thermostat returned error code: {tstat_code}. Message: {exc.response.text}"
                )
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="Thermostat timed out.")
            except httpx.RequestError as exc:
                raise HTTPException(status_code=502, detail=f"Network error contacting thermostat: {exc}")     
    

    async def update_thermostat_schedule(self, thermostat_data):
        # Send POST request to thermostat
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.schedule_url, json=thermostat_data)
                response.raise_for_status()
                raw_data = response.json()
                logger.info(f"POST request to thermostat returned: {json.dumps(raw_data, indent=2)}")        
                return raw_data
            except httpx.HTTPStatusError as exc:
                tstat_code = exc.response.status_code
                raise HTTPException(
                    status_code=502,
                    detail=f"Thermostat returned error code: {tstat_code}. Message: {exc.response.text}"
                )
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="Thermostat timed out.")
            except httpx.RequestError as exc:
                raise HTTPException(status_code=502, detail=f"Network error contacting thermostat: {exc}")


    async def set_time(self, time_data #: TimeInfo
                       ):
        """Set the thermostat time via POST to /tstat/time."""
        time_url = self.thermostat_url + "tstat/time"
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(time_url, json=time_data)
                response.raise_for_status()
                logger.info(f"Successfully set thermostat time to {time_data}")
                return response.json()
            except httpx.HTTPStatusError as exc:
                tstat_code = exc.response.status_code
                logger.error(f"Thermostat returned error code {tstat_code} when setting time: {exc.response.text}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Thermostat returned error code: {tstat_code}. Message: {exc.response.text}"
                )
            except httpx.TimeoutException:
                logger.error("Thermostat timed out when setting time")
                raise HTTPException(status_code=504, detail="Thermostat timed out.")
            except httpx.RequestError as exc:
                logger.error(f"Network error when setting thermostat time: {exc}")
                raise HTTPException(status_code=502, detail=f"Network error contacting thermostat: {exc}")


    
    async def get_state(self):
        """Fetch the current thermostat state and return as StateDTO."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(self.thermostat_url + "tstat")
                response.raise_for_status()
                raw_data = response.json()
                logger.info(f"Received thermostat state: {json.dumps(raw_data, indent=2)}")
                return raw_data
            except httpx.HTTPStatusError as exc:
                tstat_code = exc.response.status_code
                raise HTTPException(
                    status_code=502,
                    detail=f"Thermostat returned error code: {tstat_code}. Message: {exc.response.text}"
                )
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="Thermostat timed out.")
            except httpx.RequestError as exc:
                raise HTTPException(status_code=502, detail=f"Network error contacting thermostat: {exc}")            
        

            