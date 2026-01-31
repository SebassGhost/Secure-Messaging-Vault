from fastapi import FastAPI

app = FastAPI(title="Secure Messaging Vault")

@app.get("/")
def root():
    return {"status": "ok", "message": "Secure Vault API running"}

