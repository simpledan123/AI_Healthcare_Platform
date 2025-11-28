from sqlalchemy.orm import Session
from .. import models, schemas

# ID로 사용자 조회
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

# 이메일로 사용자 조회 (중복 가입 방지용)
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

# 사용자 생성
def create_user(db: Session, user: schemas.UserCreate):
    # Pydantic 모델의 데이터를 DB 모델로 변환
    # **user.dict()는 Pydantic v1 문법, v2에서는 **user.model_dump() 권장하지만
    # 호환성을 위해 개별 필드 매핑 방식을 사용하거나 dict()를 사용합니다.
    db_user = models.User(
        username=user.username,
        email=user.email,
        weight_kg=user.weight_kg,
        height_cm=user.height_cm
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user) # DB에서 생성된 ID와 시간 정보를 다시 받아옴
    return db_user