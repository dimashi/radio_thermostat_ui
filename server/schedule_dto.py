from pydantic import BaseModel
from typing import List

# Pydantic model for schedule data
class TimeSlot(BaseModel):
    time: str
    temp: float


class ScheduleData(BaseModel):
    Mon: List[TimeSlot] = []
    Tue: List[TimeSlot] = []
    Wed: List[TimeSlot] = []
    Thu: List[TimeSlot] = []
    Fri: List[TimeSlot] = []
    Sat: List[TimeSlot] = []
    Sun: List[TimeSlot] = []