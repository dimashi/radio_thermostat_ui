import asyncio
import json
import logging
import sys
import time
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent
ROOT_DIR = SERVER_DIR.parent
for path in (str(ROOT_DIR), str(SERVER_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from server.schedule_dto import ScheduleData, TimeSlot
from server.state_dto import StateDTO, TimeInfo
from thermostat.thermostat_provider import ThermostatProvider

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class Server:
    def __init__(self):
        self.thermostat = ThermostatProvider()

    async def get_thermostat_schedule(self):
    
        raw_data = await self.thermostat.get_thermostat_schedule()

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
        return await self.thermostat.update_thermostat_schedule(thermostat_data)

    async def set_time(self, time_info: TimeInfo):
        # Convert TimeInfo to dict format for JSON
        time_data = {
            "day": next(key for key, value in DAY_MAP.items() if value == time_info.day),
            "hour": time_info.hour,
            "minute": time_info.minute
        }
        return await self.thermostat.set_time(time_data)
    
                
    async def get_state(self):
        """Fetch the current thermostat state and return as StateDTO."""
        raw_data = await self.thermostat.get_state()

            
        current_time = time.localtime()
        server_time_info = TimeInfo(day=DAY_MAP[str(current_time.tm_wday)], hour=current_time.tm_hour, minute=current_time.tm_min)
        raw_data['server_time'] = server_time_info

        thermostat_time = raw_data['time']
        # convert day index to string
        thermostat_time['day'] = DAY_MAP[str(thermostat_time['day'])]
        
        # Calculate time_status based on difference between thermostat time and server time
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
                lambda t: logger.warning("Failed to set thermostat time") if t.exception() else None
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


