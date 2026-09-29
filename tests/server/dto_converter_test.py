from datetime import datetime

import pytest

from server.dto_converter import DtoConverter
from server.schedule_dto import ScheduleData, TimeSlot
from server.state_dto import TimeInfo
from thermostat.radio_thermo_program_dto import RadioThermoProgramDto
from thermostat.radio_thermo_state_dto import (
    RadioThermoStateDto,
    RadioThermoTimeInfoDto,
)


def test_thermostat_program_to_schedule_maps_days_and_times():
    program = RadioThermoProgramDto(
        root={
            "0": [450.0, 72.0, 510.0, 68.5],
            "6": [1439.0, 65.0],
        }
    )

    schedule = DtoConverter.thermostat_program_to_schedule(program)

    assert schedule.Mon == [
        TimeSlot(time="07:30", temp=72.0),
        TimeSlot(time="08:30", temp=68.5),
    ]
    assert schedule.Sun == [TimeSlot(time="23:59", temp=65.0)]
    assert schedule.Tue == []


def test_schedule_to_thermostat_program_maps_days_and_times():
    schedule = ScheduleData(
        Mon=[TimeSlot(time="07:30", temp=72.0)],
        Wed=[TimeSlot(time="08:45", temp=68.5)],
    )

    program = DtoConverter.schedule_to_thermostat_program(schedule)

    assert isinstance(program, RadioThermoProgramDto)
    assert program.root == {
        "0": [450.0, 72.0],
        "1": [],
        "2": [525.0, 68.5],
        "3": [],
        "4": [],
        "5": [],
        "6": [],
    }


def test_server_time_to_thermostat_maps_day_and_time():
    result = DtoConverter.server_time_to_thermostat(
        TimeInfo(day="Sun", hour=23, minute=45)
    )

    assert result == RadioThermoTimeInfoDto(day=6, hour=23, minute=45)


def test_thermostat_state_to_server_maps_state_and_clock_times():
    state = RadioThermoStateDto(
        temp=72.5,
        tmode=1,
        fmode=0,
        override=0,
        hold=0,
        t_heat=70.0,
        tstate=0,
        fstate=0,
        t_type_post=1,
        time=RadioThermoTimeInfoDto(day=0, hour=14, minute=30),
    )
    now = datetime(2026, 9, 21, 14, 30).astimezone()

    result = DtoConverter.thermostat_state_to_server(state, local_time=now)

    assert result.temp == 72.5
    assert result.time == TimeInfo(day="Mon", hour=14, minute=30)
    assert result.server_time == TimeInfo(day="Mon", hour=14, minute=30)
    assert result.time_status == "in sync"


@pytest.mark.parametrize(
    (
        "thermostat_day",
        "thermostat_hour",
        "thermostat_minute",
        "server_day",
        "server_hour",
        "server_minute",
        "expected",
    ),
    [
        ("Mon", 14, 30, "Mon", 14, 30, "in sync"),
        ("Mon", 14, 30, "Mon", 14, 31, "synchronizing time"),
        ("Mon", 14, 30, "Tue", 14, 30, "synchronizing time"),
        ("Sun", 23, 59, "Mon", 0, 0, "synchronizing time"),
    ],
)
def test_get_time_status(
    thermostat_day,
    thermostat_hour,
    thermostat_minute,
    server_day,
    server_hour,
    server_minute,
    expected,
):
    thermostat_time = TimeInfo(
        day=thermostat_day, hour=thermostat_hour, minute=thermostat_minute
    )
    server_time = TimeInfo(day=server_day, hour=server_hour, minute=server_minute)

    result = DtoConverter.get_time_status(thermostat_time, server_time)

    assert result == expected