import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.schedule_dto import ScheduleData, TimeSlot
from server.server import Server
from server.state_dto import StateDTO, TimeInfo
from thermostat.radio_thermo_program_dto import RadioThermoProgramDto
from thermostat.radio_thermo_state_dto import RadioThermoStateDto, RadioThermoTimeInfoDto


@pytest.mark.asyncio
async def test_get_thermostat_schedule():
    # Arrange
    server = Server()
    
    # Create mock program data
    mock_program = RadioThermoProgramDto(root={
        "0": [360.0, 70.0, 480.0, 68.0],  # Mon: 06:00 -> 70.0, 08:00 -> 68.0
        "1": [],
        "2": [],
        "3": [],
        "4": [],
        "5": [],
        "6": []
    })
    
    server.thermostat.get_heating_program = AsyncMock(return_value=mock_program)
    
    # Act
    schedule = await server.get_thermostat_schedule()
    
    # Assert
    assert isinstance(schedule, ScheduleData)
    assert len(schedule.Mon) == 2
    assert schedule.Mon[0].time == "06:00"
    assert schedule.Mon[0].temp == 70.0
    assert schedule.Mon[1].time == "08:00"
    assert schedule.Mon[1].temp == 68.0
    
    server.thermostat.get_heating_program.assert_called_once()


@pytest.mark.asyncio
async def test_update_thermostat_schedule():
    # Arrange
    server = Server()
    
    schedule_data = ScheduleData(
        Mon=[TimeSlot(time="07:30", temp=72.0)]
    )
    
    server.thermostat.update_heating_program = AsyncMock(return_value={"success": True})
    
    # Act
    result = await server.update_thermostat_schedule(schedule_data)
    
    # Assert
    assert result == {"success": True}
    server.thermostat.update_heating_program.assert_called_once()
    
    # Verify the argument sent to the client
    arg = server.thermostat.update_heating_program.call_args[0][0]
    assert isinstance(arg, RadioThermoProgramDto)
    assert arg.root["0"] == [450.0, 72.0]  # 07:30 is 450 minutes


@pytest.mark.asyncio
async def test_set_time():
    # Arrange
    server = Server()
    
    time_info = TimeInfo(day="Mon", hour=14, minute=30)
    server.thermostat.set_time = AsyncMock(return_value={"success": True})
    
    # Act
    result = await server.set_time(time_info)
    
    # Assert
    assert result == {"success": True}
    server.thermostat.set_time.assert_called_once_with({
        "day": 0,
        "hour": 14,
        "minute": 30
    })


@pytest.mark.asyncio
async def test_get_state_in_sync():
    # Arrange
    server = Server()
    
    # Monday at 14:30
    mock_now = datetime(2026, 9, 21, 14, 30)  # September 21, 2026 is a Monday (weekday=0)
    
    thermostat_state = RadioThermoStateDto(
        temp=72.5,
        tmode=1,
        fmode=0,
        override=0,
        hold=0,
        t_heat=70.0,
        tstate=0,
        fstate=0,
        t_type_post=1,
        time=RadioThermoTimeInfoDto(day=0, hour=14, minute=30)  # In sync with mock_now
    )
    
    server.thermostat.get_state = AsyncMock(return_value=thermostat_state)
    server.set_time = AsyncMock()
    
    # Patch datetime.now in server.dto_converter
    with patch("server.dto_converter.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_now
        
        # Act
        state_dto = await server.get_state()
        
    # Assert
    assert isinstance(state_dto, StateDTO)
    assert state_dto.time_status == "in sync"
    assert state_dto.temp == 72.5
    assert state_dto.time.hour == 14
    assert state_dto.time.minute == 30
    assert state_dto.server_time.hour == 14
    assert state_dto.server_time.minute == 30
    
    # Ensure set_time was NOT called/scheduled because it is in sync
    server.set_time.assert_not_called()


@pytest.mark.asyncio
async def test_get_state_out_of_sync():
    # Arrange
    server = Server()
    
    # Monday at 14:30
    mock_now = datetime(2026, 9, 21, 14, 30)  # September 21, 2026 is a Monday
    
    # Thermostat time is different (Monday 14:00) -> Out of sync!
    thermostat_state = RadioThermoStateDto(
        temp=72.5,
        tmode=1,
        fmode=0,
        override=0,
        hold=0,
        t_heat=70.0,
        tstate=0,
        fstate=0,
        t_type_post=1,
        time=RadioThermoTimeInfoDto(day=0, hour=14, minute=0)
    )
    
    server.thermostat.get_state = AsyncMock(return_value=thermostat_state)
    
    # Track calls to set_time
    set_time_called_event = asyncio.Event()
    
    async def mock_set_time(time_info):
        try:
            return {"success": True}
        finally:
            set_time_called_event.set()
            
    server.set_time = mock_set_time
    
    # Patch datetime.now in server.dto_converter
    with patch("server.dto_converter.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_now
        
        # Act
        state_dto = await server.get_state()
        
    # Assert
    assert isinstance(state_dto, StateDTO)
    assert state_dto.time_status == "synchronizing time"
    
    # Since background task is run asynchronously, wait for event or a short period
    try:
        await asyncio.wait_for(set_time_called_event.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("set_time background task was not executed")