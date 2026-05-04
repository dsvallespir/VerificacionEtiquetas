from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/", response_model=List[schemas.ProjectSummary])
def list_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Project).filter(models.Project.owner_id == current_user.id).all()


@router.post("/", response_model=schemas.ProjectOut, status_code=201)
def create_project(
    data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = models.Project(**data.model_dump(), owner_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _get_or_404(db, project_id, current_user.id)
    return project


@router.patch("/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: int,
    data: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _get_or_404(db, project_id, current_user.id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = _get_or_404(db, project_id, current_user.id)
    db.delete(project)
    db.commit()


def _get_or_404(db: Session, project_id: int, owner_id: int) -> models.Project:
    project = (
        db.query(models.Project)
        .filter(models.Project.id == project_id, models.Project.owner_id == owner_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project
