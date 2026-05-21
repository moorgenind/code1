from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app import models
from app.routers import leads, boqs, design, products, dealers, dealer_portal, auth, finance, inventory, projects, logistics, export, tasks, lightforge_portal

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
app.include_router(dealer_portal.router, prefix="/dealer-portal", tags=["Dealer Portal"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(finance.router, prefix="/finance", tags=["Finance"])
app.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(logistics.router, prefix="/logistics", tags=["Logistics"])
app.include_router(export.router, prefix="/export", tags=["Export"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
