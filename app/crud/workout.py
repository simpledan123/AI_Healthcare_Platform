from sqlalchemy.orm import Session
from .. import models, schemas

# 운동 기록 조회 (특정 사용자의 기록 목록)
def get_workouts_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.WorkoutLog)\
             .filter(models.WorkoutLog.user_id == user_id)\
             .offset(skip).limit(limit).all()

# 운동 기록 생성
def create_workout_log(db: Session, workout: schemas.WorkoutCreate, user_id: int):
    db_workout = models.WorkoutLog(
        **workout.dict(), # activity_type, duration 등 필드 자동 매핑
        user_id=user_id   # 어떤 사용자의 기록인지 명시
    )
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return db_workout