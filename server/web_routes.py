from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["Web Pages"])

# Get the base directory (parent of server directory)
BASE_DIR = Path(__file__).parent.parent

@router.get("/", response_class=FileResponse)

async def get_schedule_page():
    """Serve the schedule HTML page""" 
    html_path = BASE_DIR / "client/components/table_scheduler/scheduler.html"
    return FileResponse(html_path)