from datetime import datetime

from thermostat.radio_thermo_program_dto import RadioThermoProgramDto
from thermostat.radio_thermo_state_dto import (
    RadioThermoStateDto,
    RadioThermoTimeInfoDto,
)

from .schedule_dto import ScheduleData, TimeSlot
from .state_dto import StateDTO, TimeInfo

DAY_MAP = {
    "0": "Mon",
    "1": "Tue",
    "2": "Wed",
    "3": "Thu",
    "4": "Fri",
    "5": "Sat",
    "6": "Sun",
}

REVERSE_DAY_MAP = {value: key for key, value in DAY_MAP.items()}


def minutes_to_hhmm(total_minutes: float) -> str:
    hours = int(total_minutes // 60)
    minutes = int(total_minutes % 60)
    return f"{hours:02d}:{minutes:02d}"


def hhmm_to_minutes(time_str: str) -> int:
    hours, minutes = map(int, time_str.split(":"))
    return hours * 60 + minutes


class DtoConverter:

    @staticmethod
    def thermostat_program_to_schedule(program: RadioThermoProgramDto) -> ScheduleData:
        schedule = {}

        for day_index, day_name in DAY_MAP.items():
            schedule[day_name] = [
                TimeSlot(
                    time=minutes_to_hhmm(minute),
                    temp=temp,
                )
                for minute, temp in program.get_time_temp_pairs(day_index)
            ]

        return ScheduleData(**schedule)

    @staticmethod
    def schedule_to_thermostat_program(schedule: ScheduleData) -> RadioThermoProgramDto:
        program = RadioThermoProgramDto(root={})

        for day_name, slots in schedule.model_dump().items():
            pairs = [
                (hhmm_to_minutes(slot["time"]), float(slot["temp"]))
                for slot in slots
            ]
            program.set_time_temp_pairs(REVERSE_DAY_MAP[day_name], pairs)

        return program

    @staticmethod
    def server_time_to_thermostat(time_info: TimeInfo) -> RadioThermoTimeInfoDto:
        return RadioThermoTimeInfoDto(
            day=int(REVERSE_DAY_MAP[time_info.day]),
            hour=time_info.hour,
            minute=time_info.minute,
        )

    @staticmethod
    def get_time_info(local_time: datetime) -> TimeInfo:
        return TimeInfo(
            day=DAY_MAP[str(local_time.weekday())],
            hour=local_time.hour,
            minute=local_time.minute,
        )
    
    @staticmethod
    def thermostat_state_to_server(state: RadioThermoStateDto, local_time: datetime | None = None) -> StateDTO:
        if local_time is None:
            local_time = datetime.now().astimezone()

        thermostat_time = TimeInfo(
            day=DAY_MAP[str(state.time.day)],
            hour=state.time.hour,
            minute=state.time.minute,
        )

        server_time = DtoConverter.get_time_info(local_time)

        return StateDTO(
            temp=state.temp, 
            tmode=state.tmode,
            fmode=state.fmode,
            override=state.override,
            hold=state.hold,
            t_heat=state.t_heat,
            tstate=state.tstate,
            fstate=state.fstate,
            t_type_post=state.t_type_post,
            time=thermostat_time,
            server_time=server_time,
            time_status=DtoConverter.get_time_status(thermostat_time, server_time)
        )
  
    @staticmethod
    def get_time_status(thermostat_time, server_time):
        # Calculate time_status based on difference between thermostat time and server time
        thermostat_minutes = DtoConverter.get_total_minutes(thermostat_time)
        server_minutes = DtoConverter.get_total_minutes(server_time)
        
        diff = abs(thermostat_minutes - server_minutes)
        
        is_in_sync = diff < 1
        time_status = "in sync" if is_in_sync else "synchronizing time"
        return time_status

    @staticmethod
    def get_total_minutes(day_and_time: TimeInfo):
        day_index = int(REVERSE_DAY_MAP[day_and_time.day])
        return day_index * 24 * 60 + day_and_time.hour * 60 + day_and_time.minute