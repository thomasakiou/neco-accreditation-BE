from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.v1.endpoints import auth, data, upload, export

settings = get_settings()

app = FastAPI(title="NECO Accreditation API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(data.router, prefix="/api/v1/data", tags=["Data Management"])
app.include_router(upload.router, prefix="/api/v1/data", tags=["Bulk Import"])
app.include_router(export.router, prefix="/api/v1/data", tags=["Data Export"])

@app.get("/")
async def root():
    return {"message": "Welcome to NECO Accreditation API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
