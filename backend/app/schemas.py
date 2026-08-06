"""
Pydantic schemas used for request validation and response shaping.
"""
from datetime import datetime, time

from pydantic import BaseModel, Field, ConfigDict


class EmployeeCreate(BaseModel):
    emp_id: str = Field(..., min_length=1, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    emp_code: str = Field(..., min_length=1, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    employee_name: str = Field(..., min_length=1, max_length=150)
    department: str = Field(..., min_length=1, max_length=100)
    designation: str = Field(..., min_length=1, max_length=100)
    shift_start_time: time
    shift_end_time: time
    grace_time_minutes: int = Field(0, ge=0)
    late_entry_minutes: int = Field(0, ge=0)
    overtime_rules: str | None = None


class EmployeeUpdate(BaseModel):
    emp_code: str | None = Field(None, min_length=1, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    employee_name: str | None = None
    department: str | None = None
    designation: str | None = None
    shift_start_time: time | None = None
    shift_end_time: time | None = None
    grace_time_minutes: int | None = None
    late_entry_minutes: int | None = None
    overtime_rules: str | None = None


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    emp_id: str
    emp_code: str
    employee_name: str
    department: str
    designation: str
    shift_start_time: time
    shift_end_time: time
    grace_time_minutes: int
    late_entry_minutes: int
    overtime_rules: str | None
    is_enrolled: bool
    created_at: datetime
    updated_at: datetime


class FaceEnrollResponse(BaseModel):
    emp_id: str
    emp_code: str
    is_enrolled: bool
    message: str


class FaceMatchResult(BaseModel):
    matched: bool
    emp_id: str | None = None
    emp_code: str | None = None
    employee_name: str | None = None
    distance: float | None = None


class PhotoValidationResult(BaseModel):
    valid: bool
    message: str