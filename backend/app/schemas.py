from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
from app.models import ProjectStatus, LabelStep, DifferenceType, ComparisonStatus


# ─── User ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


# ─── Project ─────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    product_name: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    product_name: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    product_name: Optional[str]
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    owner_id: int
    owner: UserOut

    model_config = {"from_attributes": True}


class ProjectSummary(BaseModel):
    id: int
    name: str
    product_name: Optional[str]
    status: ProjectStatus
    created_at: datetime
    owner: UserOut

    model_config = {"from_attributes": True}


# ─── LabelVersion ────────────────────────────────────────────────────────────

class LabelVersionOut(BaseModel):
    id: int
    step: LabelStep
    image_path: str
    annotated_image_path: Optional[str]
    notes: Optional[str]
    uploaded_at: datetime
    project_id: int
    uploader: Optional[UserOut] = None

    model_config = {"from_attributes": True}


# ─── Difference ──────────────────────────────────────────────────────────────

class DifferenceOut(BaseModel):
    id: int
    difference_type: DifferenceType
    description: str
    bbox_x: Optional[int]
    bbox_y: Optional[int]
    bbox_w: Optional[int]
    bbox_h: Optional[int]
    severity: str
    extra_data: Optional[dict]

    model_config = {"from_attributes": True}


# ─── Comparison ──────────────────────────────────────────────────────────────

class ComparisonOut(BaseModel):
    id: int
    status: ComparisonStatus
    similarity_score: Optional[float]
    ocr_score: Optional[float]
    color_score: Optional[float]
    compared_at: datetime
    reviewer_notes: Optional[str]
    base_version_id: int
    revised_version_id: int
    differences: List[DifferenceOut] = []

    model_config = {"from_attributes": True}


class ComparisonReview(BaseModel):
    status: ComparisonStatus
    reviewer_notes: Optional[str] = None


# ─── Report ──────────────────────────────────────────────────────────────────

class ReportOut(BaseModel):
    id: int
    title: str
    content: Optional[str]
    generated_at: datetime
    file_path: Optional[str]
    project_id: int
    comparison_id: Optional[int]

    model_config = {"from_attributes": True}
