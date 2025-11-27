from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ... import schemas, crud, database

router = APIRouter(
    prefix="/community",
    tags=["Community"]
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# [피드 조회]
@router.get("/feed", response_model=List[schemas.Post])
def read_feed(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.community.get_posts(db, skip=skip, limit=limit)

# [글 작성]
@router.post("/posts/{user_id}", response_model=schemas.Post)
def create_post(user_id: int, post: schemas.PostCreate, db: Session = Depends(get_db)):
    return crud.community.create_post(db=db, post=post, user_id=user_id)