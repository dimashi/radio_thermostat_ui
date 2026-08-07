from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["Web Pages"])

BASE_DIR = Path(__file__).parent.parent

@router.get("/", response_class=FileResponse)

async def get_schedule_page():
    """Serve the schedule HTML page""" 
    return FileResponse(BASE_DIR / "client/components/table_scheduler/scheduler.html")