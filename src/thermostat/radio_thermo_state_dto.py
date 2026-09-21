from pydantic import BaseModel


class RadioThermoTimeInfoDto(BaseModel):
    """Time information nested within thermostat state"""
    day: int
    hour: int
    minute: int


class RadioThermoStateDto(BaseModel):
    """Thermostat state data transfer object"""
    temp: float
    tmode: int
    fmode: int
    override: int
    hold: int
    t_heat: float
    tstate: int
    fstate: int
    t_type_post: int
    time: RadioThermoTimeInfoDto
