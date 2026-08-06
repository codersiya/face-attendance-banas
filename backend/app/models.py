"""
ORM models.

Design notes:
- emp_id is the primary key: a user-entered, human-readable string
  (e.g. "EMP0091" or "BNS-2044"). There is no separate internal integer ID.
- emp_code is a second user-entered string field, unique + indexed, distinct
  from emp_id.
- One row per employee. All three face embeddings (front / left / right)
  are stored as separate columns on that same row.
- No pgvector extension is used. Embeddings are stored using PostgreSQL's
  native ARRAY type (double precision[]).
"""
from datetime import datetime, time

from sqlalchemy import Integer, String, Time, Text, DateTime, ARRAY, Float, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

EMBEDDING_DIM = 128


class Employee(Base):
    __tablename__ = "employees"

    emp_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    emp_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)

    employee_name: Mapped[str] = mapped_column(String(150), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)

    shift_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    shift_end_time: Mapped[time] = mapped_column(Time, nullable=False)

    grace_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    late_entry_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overtime_rules: Mapped[str] = mapped_column(Text, nullable=True)

    embedding_front: Mapped[list] = mapped_column(ARRAY(Float, dimensions=1), nullable=True)
    embedding_left: Mapped[list] = mapped_column(ARRAY(Float, dimensions=1), nullable=True)
    embedding_right: Mapped[list] = mapped_column(ARRAY(Float, dimensions=1), nullable=True)

    is_enrolled: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )