from unittest.mock import AsyncMock, patch

import httpx
import pytest

from thermostat.radio_thermo_api_client import RadioThermoApiClient
from thermostat.radio_thermo_program_dto import RadioThermoProgramDto
from thermostat.radio_thermo_state_dto import RadioThermoTimeInfoDto

# Tests for error conditions only

@pytest.mark.parametrize(
    ("client_method", "http_method", "url_accessor", "arguments"),
    [
        (
            RadioThermoApiClient.get_heating_program,
            "get",
            lambda client: client.heating_program_url,
             ()
        ),
        (
            RadioThermoApiClient.update_heating_program,
            "post",
            lambda client: client.heating_program_url,
            (RadioThermoProgramDto(root={}),),
        ),
        (
            RadioThermoApiClient.get_state,
            "get",  
            lambda client: client.tstat_url,
            ()
        ),
        (
            RadioThermoApiClient.set_time,
            "post",
            lambda client: client.time_url,
            (RadioThermoTimeInfoDto(day=0, hour=12, minute=0),),
        )
    ],
)
@pytest.mark.parametrize("error_type", ["http_status", "timeout", "request"])
@pytest.mark.asyncio
async def test_other_api_methods_propagate_http_errors_mock(
    client_method, http_method, url_accessor, arguments, error_type
):
    client = RadioThermoApiClient()
    request = httpx.Request(http_method.upper(), url_accessor(client))

    if error_type == "http_status":
        response = httpx.Response(
            status_code=500, request=request, text="Internal Server Error"
        )
        exc = httpx.HTTPStatusError("Error", request=request, response=response)
        expected_exception = httpx.HTTPStatusError
    elif error_type == "timeout":
        exc = httpx.ConnectTimeout("Connection timed out", request=request)
        expected_exception = httpx.TimeoutException
    else:
        exc = httpx.RequestError("Network error", request=request)
        expected_exception = httpx.RequestError

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    getattr(mock_client, http_method).side_effect = exc

    with patch("httpx.AsyncClient", return_value=mock_client), pytest.raises(
        expected_exception
    ) as exc_info:
        await client_method(client, *arguments)

    if error_type == "http_status":
        assert exc_info.value.response.status_code == 500
