from unittest.mock import AsyncMock

import pytest

from server import api_routes
from server.schedule_dto import ScheduleData, TimeSlot
from server.state_dto import StateDTO, TimeInfo


@pytest.mark.asyncio
async def test_get_schedule_delegates_to_server(monkeypatch):
    schedule = ScheduleData(Mon=[TimeSlot(time="06:00", temp=68.0)])
    mock_server = AsyncMock()
    mock_server.get_thermostat_schedule.return_value = schedule
    monkeypatch.setattr(api_routes, "server", mock_server)

    result = await api_routes.get_schedule()

    assert result is schedule
    mock_server.get_thermostat_schedule.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_update_schedule_delegates_schedule_to_server(monkeypatch):
    schedule = ScheduleData(Tue=[TimeSlot(time="07:30", temp=70.0)])
    mock_server = AsyncMock()
    mock_server.update_thermostat_schedule.return_value = {"success": True}
    monkeypatch.setattr(api_routes, "server", mock_server)

    result = await api_routes.update_schedule(schedule)

    assert result == {"success": True}
    mock_server.update_thermostat_schedule.assert_awaited_once_with(schedule)


@pytest.mark.asyncio
async def test_get_state_delegates_to_server(monkeypatch):
    state = StateDTO(
        temp=72.5,
        tmode=1,
        fmode=0,
        override=0,
        hold=0,
        t_heat=70.0,
        tstate=0,
        fstate=0,
        t_type_post=1,
        time=TimeInfo(day="Mon", hour=14, minute=30),
        server_time=TimeInfo(day="Mon", hour=14, minute=30),
        time_status="in sync",
    )
    mock_server = AsyncMock()
    mock_server.get_state.return_value = state
    monkeypatch.setattr(api_routes, "server", mock_server)

    result = await api_routes.get_state()

    assert result is state
    mock_server.get_state.assert_awaited_once_with()