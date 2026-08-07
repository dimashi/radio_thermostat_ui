#!/usr/bin/env python3
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from server.web_routes import BASE_DIR
from server.web_routes import router as web_router

app = FastAPI(title="Radio Thermostat Scheduler API")

app.router.include_router(web_router)

# Serve static assets: CSS and JS directories
app.mount("/css", StaticFiles(directory=BASE_DIR / "client" / "css"), name="css")
app.mount("/js", StaticFiles(directory=BASE_DIR / "client" / "js"), name="js")

# Lazy load API routes:
_api_router_loaded = False

@app.middleware("http")
async def traffic_middleware(request: Request, call_next):
    global _api_router_loaded
    
    # Only trigger when an /api request comes in for the first time
    if not _api_router_loaded and request.url.path.startswith("/api"):
        # Import the heavy module ONLY when an API route is actually called
        from server.api_routes import router as api_router
        
        # Include the router into FastAPI's runtime route table
        app.include_router(api_router)
        _api_router_loaded = True

    if _api_router_loaded:
        from server.api_routes import get_monitor
        get_monitor().record_hit() # Always recording, even on cache hits

    return await call_next(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
