import asyncio
from unittest.mock import AsyncMock

import pytest

from server.caching_sequential_server import CachingSequentialServer
from server.schedule_dto import ScheduleData, TimeSlot
from server.server_interface import ServerInterface
from server.state_dto import StateDTO, TimeInfo


def make_state(temp: float) -> StateDTO:
    time_info = TimeInfo(day="Mon", hour=12, minute=0)
    return StateDTO(
        temp=temp,
        tmode=1,
        fmode=0,
        override=0,
        hold=0,
        t_heat=68.0,
        tstate=0,
        fstate=0,
        t_type_post=1,
        time=time_info,
        server_time=time_info,
        time_status="in sync",
    )


@pytest.mark.asyncio
async def test_schedule_reads_are_cached():
    server = AsyncMock(spec=ServerInterface)
    server.get_thermostat_schedule.return_value = ScheduleData(
        Mon=[TimeSlot(time="06:00", temp=68.0)]
    )
    caching_server = CachingSequentialServer(server)

    first_read = await caching_server.get_thermostat_schedule()
    second_read = await caching_server.get_thermostat_schedule()

    assert first_read == second_read
    assert second_read.Mon == [TimeSlot(time="06:00", temp=68.0)]
    server.get_thermostat_schedule.assert_awaited_once()


@pytest.mark.asyncio
async def test_successful_schedule_update_refreshes_cache():
    server = AsyncMock(spec=ServerInterface)
    server.update_thermostat_schedule.return_value = {"success": True}
    updated_schedule = ScheduleData(
        Tue=[TimeSlot(time="07:30", temp=70.0)]
    )
    caching_server = CachingSequentialServer(server)

    result = await caching_server.update_thermostat_schedule(updated_schedule)
    cached_schedule = await caching_server.get_thermostat_schedule()

    assert result == {"success": True}
    assert cached_schedule == updated_schedule
    server.update_thermostat_schedule.assert_awaited_once_with(updated_schedule)
    server.get_thermostat_schedule.assert_not_awaited()


@pytest.mark.asyncio
async def test_server_operations_are_serialized():
    server = AsyncMock(spec=ServerInterface)
    first_call_started = asyncio.Event()
    release_first_call = asyncio.Event()
    active_calls = 0
    max_active_calls = 0

    async def set_time(_time_info):
        nonlocal active_calls, max_active_calls
        active_calls += 1
        max_active_calls = max(max_active_calls, active_calls)
        if active_calls == 1:
            first_call_started.set()
            await release_first_call.wait()
        active_calls -= 1

    server.set_time.side_effect = set_time
    caching_server = CachingSequentialServer(server)
    time_info = TimeInfo(day="Mon", hour=12, minute=0)

    first_task = asyncio.create_task(caching_server.set_time(time_info))
    await first_call_started.wait()
    second_task = asyncio.create_task(caching_server.set_time(time_info))
    await asyncio.sleep(0)

    assert max_active_calls == 1
    release_first_call.set()
    await asyncio.gather(first_task, second_task)

    assert max_active_calls == 1
    assert server.set_time.await_count == 2


@pytest.mark.asyncio
async def test_background_refresh_updates_schedule_and_state_cache(monkeypatch):
    monkeypatch.setattr(
        "server.caching_sequential_server.settings.cache_ttl_seconds", 0.01
    )
    server = AsyncMock(spec=ServerInterface)
    schedules = [
        ScheduleData(Mon=[TimeSlot(time="06:00", temp=68.0)]),
        ScheduleData(Mon=[TimeSlot(time="07:00", temp=70.0)]),
    ]
    server.get_thermostat_schedule.side_effect = schedules
    states = [make_state(68.0), make_state(70.0)]
    refresh_finished = asyncio.Event()
    state_calls = 0

    async def mark_second_refresh():
        nonlocal state_calls
        state_calls += 1
        if state_calls == 2:
            refresh_finished.set()
        return states[min(state_calls - 1, 1)]

    server.get_state.side_effect = mark_second_refresh
    caching_server = CachingSequentialServer(server)

    await caching_server.start_background_refresh()
    try:
        await asyncio.wait_for(refresh_finished.wait(), timeout=1.0)
        schedule = await caching_server.get_thermostat_schedule()
        state = await caching_server.get_state()
    finally:
        await caching_server.stop_background_refresh()

    assert schedule.Mon == [TimeSlot(time="07:00", temp=70.0)]
    assert state.temp == 70.0
    assert server.get_thermostat_schedule.await_count == 2
    assert server.get_state.await_count == 2