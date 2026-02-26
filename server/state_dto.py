from pydantic import BaseModel


class TimeInfo(BaseModel):
    """Time information nested within thermostat state"""
    day: int
    hour: int
    minute: int


class StateDTO(BaseModel):
    """Thermostat state data transfer object"""
    temp: float
    tmode: int
    fmode: int
    override: int
    hold: int
    t_heat: float
    tstate: int
    fstate: int
    time: TimeInfo
    t_type_post: int
