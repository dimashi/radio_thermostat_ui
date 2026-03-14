import httpx
import json
import logging
import time
import asyncio
from fastapi import HTTPException
from schedule_dto import ScheduleData, TimeSlot
from state_dto import StateDTO, TimeInfo

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class Server:
    def __init__(self):
        self.schedule_url = "http://thermostat-22-33-6A/tstat/program/heat"

    async def get_thermostat_schedule(self):
    
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(self.schedule_url)
                response.raise_for_status()
                raw_data = response.json()
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

        logger.info(f"Received data from thermostat: {json.dumps(raw_data, indent=2)}")

        # Initialize the result dictionary
        schedule_dict = {day: [] for day in DAY_MAP.values()}

        for day_index, values in raw_data.items():
            day_name = DAY_MAP.get(day_index)
            if not day_name:
                continue
        
            # The list is [time, temp, time, temp...] -> pair them up
            # zip(list[0::2], list[1::2]) creates pairs of (time, temp)
            for time_min, temp in zip(values[0::2], values[1::2]):
                schedule_dict[day_name].append(
                    TimeSlot(time=minutes_to_hhmm(time_min), temp=float(temp))
                )

        return ScheduleData(**schedule_dict)


    async def update_thermostat_schedule(self, schedule_data: ScheduleData):
        
        # Convert ScheduleData to thermostat format
        thermostat_data = {}
        
        # Reverse DAY_MAP: day name -> day number
        reverse_day_map = {v: k for k, v in DAY_MAP.items()}
        
        # Convert schedule_data to dict
        schedule_dict = schedule_data.model_dump()
        
        for day_name, time_slots in schedule_dict.items():
            day_index = reverse_day_map.get(day_name)
            if day_index is None:
                continue
            
            # Convert list of TimeSlot to flat array [time_min, temp, time_min, temp...]
            flat_array = []
            for time_slot in time_slots:
                # Convert HH:MM to minutes since midnight
                time_min = hhmm_to_minutes(time_slot['time'])
                flat_array.append(time_min)
                flat_array.append(int(time_slot['temp']))
            
            thermostat_data[day_index] = flat_array

        # print("Sending POST request with data:")
        # print(json.dumps(thermostat_data, indent=2))
        logger.info(f"Sending POST request to thermostat: {json.dumps(thermostat_data, indent=2)}")


        # return {"status": "success", "message": "Schedule updated on thermostat"}
        
        # Send POST request to thermostat
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.schedule_url, json=thermostat_data)
                response.raise_for_status()
                raw_data = response.json()
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

            logger.info(f"POST request to thermostat returned: {json.dumps(raw_data, indent=2)}")
        
            return raw_data

    async def set_time(self, time_info: TimeInfo):
        """Set the thermostat time via POST to /tstat/time."""
        time_url = "http://thermostat-22-33-6A/tstat/time"
        
        # Convert TimeInfo to dict format for JSON
        time_data = {
            "day": time_info.day,
            "hour": time_info.hour,
            "minute": time_info.minute
        }
        
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
        state_url = "http://thermostat-22-33-6A/tstat"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(state_url)
                response.raise_for_status()
                raw_data = response.json()
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

            logger.info(f"Received thermostat state: {json.dumps(raw_data, indent=2)}")
            current_time = time.localtime()
            server_time_info = TimeInfo(day=current_time.tm_wday, hour=current_time.tm_hour, minute=current_time.tm_min)
            raw_data['server_time'] = server_time_info
            
            # Calculate time_status based on difference between thermostat time and server time
            thermostat_time = raw_data['time']
            thermostat_minutes = thermostat_time['hour'] * 60 + thermostat_time['minute']
            server_minutes = server_time_info.hour * 60 + server_time_info.minute
            
            diff = abs(thermostat_minutes - server_minutes)
            # Handle day wrap-around
            if diff > 12 * 60:
                diff = 24 * 60 - diff
            
            is_in_sync = diff < 1
            raw_data['time_status'] = "in sync" if is_in_sync else "synchronizing time"
            
            # If time is out of sync, attempt to sync it in the background
            if not is_in_sync:
                task = asyncio.create_task(self.set_time(server_time_info))
                # Add error callback to log failures
                task.add_done_callback(
                    lambda t: logger.warning(f"Failed to set thermostat time") if t.exception() else None
                )
            
            return StateDTO(**raw_data)

# --- Helper Logic ---
def minutes_to_hhmm(total_minutes: int) -> str:
    """Converts minutes since midnight to 24-hour HH:MM format."""
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"

def hhmm_to_minutes(time_str: str) -> int:
    """Converts 24-hour HH:MM format to minutes since midnight."""
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes

DAY_MAP = {
    "0": "Mon", "1": "Tue", "2": "Wed", "3": "Thu", 
    "4": "Fri", "5": "Sat", "6": "Sun"
}


    