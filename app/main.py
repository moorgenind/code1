from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app import models
from app.routers import leads, boqs, design, products, dealers

load_dotenv()

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Morgan Innovations", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Morgan Innovations backend is running"}

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(leads.router, prefix="/leads", tags=["Leads"])
app.include_router(boqs.router, prefix="/boqs", tags=["BOQs"])
app.include_router(design.router, prefix="/design", tags=["Design Requests"])
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(dealers.router, prefix="/dealers", tags=["Dealers"])
