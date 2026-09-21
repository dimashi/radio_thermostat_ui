import socket
from urllib.parse import urlparse

import pytest

from config.settings import settings
from thermostat.radio_thermo_api_client import RadioThermoApiClient
from thermostat.radio_thermo_program_dto import RadioThermoProgramDto


def is_thermostat_reachable() -> bool:
    """Helper to check if the physical thermostat IP is reachable on port 80."""
    parsed = urlparse(settings.thermostat_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    
    try:
        with socket.create_connection((host, port), timeout=2.0):
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