from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.database.connection import DatabaseError
from app.routers import address_routes, user_routes

app = FastAPI(
    title=settings.app_name,
    description="Customer profiles and delivery addresses for ShopEase. Users are identified by the JWT issued by the Authentication Service.",
    version="1.0.0",
)

app.include_router(user_routes.router)
app.include_router(address_routes.router)


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    return JSONResponse(status_code=500, content={"detail": "Database error, please try again"})


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "user-service"}
