from fastapi import FastAPI

app = FastAPI(title="ERP Backend Test")

@app.get("/")
def root():
    return {"status": "ok", "message": "FastAPI backend funcionando"}

@app.get("/health")
def health():
    return {"status": "healthy"}
