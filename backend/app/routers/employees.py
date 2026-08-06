"""
Employee CRUD + face enrollment endpoints.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee
from app.face_service import analyze_and_validate, euclidean_distance, VALID_POSES
from app.config import settings
from app.schemas import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeOut,
    FaceEnrollResponse,
    FaceMatchResult,
    PhotoValidationResult,
)

logger = logging.getLogger("app.employees")

router = APIRouter(prefix="/api/employees", tags=["employees"])

MAX_IMAGE_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB per photo
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def _read_and_validate_image(upload: UploadFile) -> bytes:
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type '{upload.content_type}' for {upload.filename}.",
        )
    data = await upload.read()
    if len(data) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{upload.filename} exceeds the 8MB limit.",
        )
    return data


def _get_employee_or_404(db: Session, emp_id: str) -> Employee:
    employee = db.get(Employee, emp_id)
    if employee is None:
        raise HTTPException(status_code=404, detail=f"Employee '{emp_id}' not found.")
    return employee


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    employee = Employee(**payload.model_dump())
    db.add(employee)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning("Duplicate employee create attempt: emp_id=%s emp_code=%s", payload.emp_id, payload.emp_code)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee ID '{payload.emp_id}' or Employee Code '{payload.emp_code}' is already in use.",
        )
    db.refresh(employee)
    logger.info("Employee created: %s", employee.emp_id)
    return employee


# ---------------------------------------------------------------------------
# Step 2: Enroll the 3 required face images (front / left / right).
# Uses the SAME pose-aware validation as /validate-photo so a photo that
# passed pre-check here is guaranteed to pass again (barring lighting
# changes between capture and final submit).
# ---------------------------------------------------------------------------
@router.post("/{emp_id}/enroll-faces", response_model=FaceEnrollResponse)
async def enroll_faces(
    emp_id: str,
    front_image: UploadFile = File(..., description="Front-facing photo"),
    left_image: UploadFile = File(..., description="Left profile photo"),
    right_image: UploadFile = File(..., description="Right profile photo"),
    db: Session = Depends(get_db),
):
    employee = _get_employee_or_404(db, emp_id)

    front_bytes = await _read_and_validate_image(front_image)
    left_bytes = await _read_and_validate_image(left_image)
    right_bytes = await _read_and_validate_image(right_image)

    front_result = analyze_and_validate(front_bytes, "front")
    if not front_result["valid"]:
        raise HTTPException(status_code=422, detail=f"Front photo: {front_result['message']}")

    left_result = analyze_and_validate(left_bytes, "left")
    if not left_result["valid"]:
        raise HTTPException(status_code=422, detail=f"Left profile photo: {left_result['message']}")

    right_result = analyze_and_validate(right_bytes, "right")
    if not right_result["valid"]:
        raise HTTPException(status_code=422, detail=f"Right profile photo: {right_result['message']}")

    employee.embedding_front = front_result["embedding"]
    employee.embedding_left = left_result["embedding"]
    employee.embedding_right = right_result["embedding"]
    employee.is_enrolled = True

    db.add(employee)
    db.commit()

    logger.info("Face enrollment completed: %s", employee.emp_id)

    return FaceEnrollResponse(
        emp_id=employee.emp_id,
        emp_code=employee.emp_code,
        is_enrolled=True,
        message="All 3 face embeddings generated and stored successfully.",
    )


@router.get("", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    return db.execute(select(Employee).order_by(Employee.emp_id)).scalars().all()


@router.get("/{emp_id}", response_model=EmployeeOut)
def get_employee(emp_id: str, db: Session = Depends(get_db)):
    return _get_employee_or_404(db, emp_id)


@router.put("/{emp_id}", response_model=EmployeeOut)
def update_employee(emp_id: str, payload: EmployeeUpdate, db: Session = Depends(get_db)):
    employee = _get_employee_or_404(db, emp_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.add(employee)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That Employee Code is already in use by another employee.",
        )
    db.refresh(employee)
    return employee


@router.delete("/{emp_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(emp_id: str, db: Session = Depends(get_db)):
    employee = _get_employee_or_404(db, emp_id)
    db.delete(employee)
    db.commit()


@router.post("/match", response_model=FaceMatchResult)
async def match_face(image: UploadFile = File(...), db: Session = Depends(get_db)):
    image_bytes = await _read_and_validate_image(image)
    result = analyze_and_validate(image_bytes, "front")
    if not result["valid"]:
        raise HTTPException(status_code=422, detail=result["message"])
    probe_embedding = result["embedding"]

    employees = db.execute(select(Employee).where(Employee.is_enrolled.is_(True))).scalars().all()

    best_employee = None
    best_distance = None

    for emp in employees:
        for stored in (emp.embedding_front, emp.embedding_left, emp.embedding_right):
            if stored is None:
                continue
            dist = euclidean_distance(probe_embedding, list(stored))
            if best_distance is None or dist < best_distance:
                best_distance = dist
                best_employee = emp

    if best_employee is not None and best_distance is not None and best_distance <= settings.FACE_MATCH_TOLERANCE:
        return FaceMatchResult(
            matched=True,
            emp_id=best_employee.emp_id,
            emp_code=best_employee.emp_code,
            employee_name=best_employee.employee_name,
            distance=round(best_distance, 4),
        )

    return FaceMatchResult(matched=False, distance=round(best_distance, 4) if best_distance else None)


# ---------------------------------------------------------------------------
# Validate a single photo immediately after capture, before final submit.
# Does NOT touch the database. `pose` tells the validator which shot this
# is meant to be, so it can check BOTH face quality AND head angle.
# ---------------------------------------------------------------------------
@router.post("/validate-photo", response_model=PhotoValidationResult)
async def validate_photo(image: UploadFile = File(...), pose: str = Form(...)):
    if pose not in VALID_POSES:
        raise HTTPException(status_code=400, detail=f"pose must be one of {sorted(VALID_POSES)}")

    image_bytes = await _read_and_validate_image(image)
    result = analyze_and_validate(image_bytes, pose)
    return PhotoValidationResult(valid=result["valid"], message=result["message"])