import pydantic


# Pydantic model for schedule data
class TimeSlot(pydantic.BaseModel):
    time: str
    temp: float


class ScheduleData(pydantic.BaseModel):
    Mon: list[TimeSlot] = []
    Tue: list[TimeSlot] = []
    Wed: list[TimeSlot] = []
    Thu: list[TimeSlot] = []
    Fri: list[TimeSlot] = []
    Sat: list[TimeSlot] = []
    Sun: list[TimeSlot] = []