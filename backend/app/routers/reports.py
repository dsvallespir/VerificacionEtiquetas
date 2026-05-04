from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services.auth import get_current_user
from app.services.report_builder import build_report_content

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/{project_id}/generate", response_model=schemas.ReportOut, status_code=201)
def generate_report(
    project_id: int,
    comparison_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    comparison = db.query(models.Comparison).filter(models.Comparison.id == comparison_id).first()
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparación no encontrada")

    content = build_report_content(project, comparison)
    step_label = comparison.revised_version.step.value.replace("_", " ").title()

    report = models.Report(
        title=f"Reporte - {project.name} - {step_label}",
        content=content,
        project_id=project_id,
        comparison_id=comparison_id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/{project_id}", response_model=List[schemas.ReportOut])
def list_reports(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project.reports


@router.get("/detail/{report_id}", response_model=schemas.ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    # Verificar pertenencia
    project = db.query(models.Project).filter(
        models.Project.id == report.project_id,
        models.Project.owner_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="Sin permisos")

    return report
