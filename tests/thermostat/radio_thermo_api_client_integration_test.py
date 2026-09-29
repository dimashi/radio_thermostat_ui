import socket
from urllib.parse import urlparse

import pytest

from config.settings import settings
from thermostat.radio_thermo_api_client import RadioThermoApiClient
from thermostat.radio_thermo_program_dto import RadioThermoProgramDto
from thermostat.radio_thermo_state_dto import (
    RadioThermoStateDto,
    RadioThermoTimeInfoDto,
)


def is_thermostat_reachable() -> bool:
    """Helper to check if the physical thermostat IP is reachable on port 80."""
    parsed = urlparse(settings.thermostat_url)
    if parsed.hostname is None:
        return False
    # If port is None, default to 80 for HTTP and 443 for HTTPS
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    
    try:
        with socket.create_connection((parsed.hostname, port), timeout=2.0):
            return True
    except (OSError, TimeoutError):
        return False


# Skip all tests in this file if the physical hardware is offline
pytestmark = pytest.mark.skipif(
    not is_thermostat_reachable(),
    reason=f"Thermostat at {settings.thermostat_url} is unreachable on local network."
)


@pytest.mark.asyncio
async def test_get_heating_program():
    """Integration test against physical Radio Thermostat hardware."""
    client = RadioThermoApiClient()
    
    # Execute actual HTTP request to device
    program = await client.get_heating_program()
    
    # Assertions on live hardware response
    assert isinstance(program, RadioThermoProgramDto)
    
    # Verify thermostat returned all 7 days of the week (keys '0' through '6')
    for day_code in range(7):
        assert str(day_code) in program.root or day_code in program.root
        
    # Verify setpoints list structure (must have even number of elements: time, temp pairs)
    day_zero_schedule = program.root.get("0") or program.root.get(0)
    assert len(day_zero_schedule) % 2 == 0


@pytest.mark.asyncio
async def test_get_state():
    """Integration test for get_state against physical Radio Thermostat hardware."""
    client = RadioThermoApiClient()
    
    # Execute actual HTTP request to device
    state = await client.get_state()
    
    # Assertions on live hardware response
    assert isinstance(state, RadioThermoStateDto)
    assert isinstance(state.temp, float)
    assert isinstance(state.tmode, int)
    assert isinstance(state.fmode, int)
    assert isinstance(state.override, int)
    assert isinstance(state.hold, int)
    assert isinstance(state.t_heat, float)
    assert isinstance(state.tstate, int)
    assert isinstance(state.fstate, int)
    assert isinstance(state.t_type_post, int)
    
    # Verify time info is correctly populated
    assert state.time is not None
    assert isinstance(state.time.day, int)
    assert 0 <= state.time.day <= 6
    assert isinstance(state.time.hour, int)
    assert 0 <= state.time.hour <= 23
    assert isinstance(state.time.minute, int)
    assert 0 <= state.time.minute <= 59


@pytest.mark.asyncio
async def test_update_heating_program():
    """Integration test for update_heating_program against physical Radio Thermostat hardware."""
    client = RadioThermoApiClient()
    
    # 1. Fetch original heating program to restore later
    original_program = await client.get_heating_program()
    assert isinstance(original_program, RadioThermoProgramDto)
    
    # 2. Prepare an update (modify day "0" slightly, keeping a valid even-length list structure)
    updated_root = {str(k): list(v) for k, v in original_program.root.items()}
    day_zero_key = "0"
    
    if day_zero_key not in updated_root:
        updated_root[day_zero_key] = [360.0, 70.0, 480.0, 68.0]
    else:
        # Toggle the first target temperature slightly (index 1)
        if len(updated_root[day_zero_key]) >= 2:
            updated_root[day_zero_key][1] = 68.0 if updated_root[day_zero_key][1] != 68.0 else 69.0
            
    updated_program = RadioThermoProgramDto(root=updated_root)
    
    try:
        # 3. Write updated program
        result = await client.update_heating_program(updated_program)
        assert isinstance(result, dict)
        
        # 4. Fetch program again and verify update was written
        new_program = await client.get_heating_program()
        assert new_program.root[day_zero_key] == updated_program.root[day_zero_key]
        
    finally:
        # 5. Restore original program to physical hardware to avoid side-effects
        await client.update_heating_program(original_program)


@pytest.mark.asyncio
async def test_set_time():
    """Integration test for set_time against physical Radio Thermostat hardware."""
    client = RadioThermoApiClient()
    
    # 1. Fetch current state to get original time
    original_state = await client.get_state()
    original_time = original_state.time
    
    # 2. Choose a new valid time (toggle minute slightly)
    test_day = original_time.day
    test_hour = original_time.hour
    test_minute = (original_time.minute + 5) % 60
    
    test_time_data = RadioThermoTimeInfoDto(
        day=test_day,
        hour=test_hour,
        minute=test_minute
    )
    
    try:
        # 3. Set the test time
        result = await client.set_time(test_time_data)
        assert isinstance(result, dict)
        
        # 4. Fetch current state and verify time has been updated
        new_state = await client.get_state()
        assert new_state.time.hour == test_hour
        assert abs(new_state.time.minute - test_minute) <= 1
        
    finally:
        # 5. Restore the original time
        await client.set_time(original_time)

