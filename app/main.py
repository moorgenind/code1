from dotenv import load_dotenv
from fastapi import FastAPI
from app.database import engine
from app import models
from app.routers import leads, boqs, design

load_dotenv()

# Create tables
models.Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(title="Morgan Innovations", version="2.0")


@app.get("/")
def root():
    return {"message": "Morgan Innovations backend is running"}


@app.get("/health")
def health():
    return {"ok": True}


# Routers
app.include_router(leads.router, prefix="/leads", tags=["Leads"])
app.include_router(boqs.router, prefix="/boqs", tags=["BOQs"])
app.include_router(design.router, prefix="/design", tags=["Design Requests"])