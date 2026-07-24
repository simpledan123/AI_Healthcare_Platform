from sqlalchemy.orm import Session

from .models import ReferenceExercise
from .services.demo_data import demo_reference_payload


def seed_demo_reference(db: Session) -> ReferenceExercise:
    payload = demo_reference_payload()
    reference = db.get(ReferenceExercise, payload["id"])
    if reference:
        return reference
    reference = ReferenceExercise(**payload)
    db.add(reference)
    db.commit()
    db.refresh(reference)
    return reference

