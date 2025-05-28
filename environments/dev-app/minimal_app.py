# minimal_app.py
from fastapi import FastAPI, Request
import uvicorn
import time

app = FastAPI(title="Minimal Image Management API")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    print(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}s")
    return response

@app.get("/")
async def root():
    return {"message": "Welcome to the Minimal Image Management API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("minimal_app:app", host="0.0.0.0", port=8000, reload=True)
