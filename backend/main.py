from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import models, schemas

app = FastAPI(
    title="Business Management System",
    description="A flexible business management system for different types of businesses.",
    version="0.1.0"
)

Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {
        "message": "Business Management System API is running successfully!"
    }


@app.post("/businesses/", response_model=schemas.BusinessResponse, status_code=201)
def create_business(
    business: schemas.BusinessCreate,
    db: Session = Depends(get_db)
):
    new_business = models.Business(
        name=business.name,
        business_type=business.business_type
    )

    db.add(new_business)
    db.commit()
    db.refresh(new_business)

    return new_business


@app.get("/businesses/", response_model=list[schemas.BusinessResponse])
def get_businesses(db: Session = Depends(get_db)):
    return db.query(models.Business).all()