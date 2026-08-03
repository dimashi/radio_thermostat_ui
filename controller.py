#!/usr/bin/env python3
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from server.api_routes import get_monitor
from server.api_routes import router as api_router
from server.web_routes import BASE_DIR
from server.web_routes import router as web_router

app = FastAPI(title="Radio Thermostat Scheduler API")

app.router.include_router(api_router)
app.router.include_router(web_router)

# Serve static assets: CSS and JS directories
app.mount("/css", StaticFiles(directory=BASE_DIR / "client" / "css"), name="css")
app.mount("/js", StaticFiles(directory=BASE_DIR / "client" / "js"), name="js")

@app.middleware("http")
async def traffic_middleware(request: Request, call_next):
    get_monitor().record_hit() # Always recording, even on cache hits
    return await call_next(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
