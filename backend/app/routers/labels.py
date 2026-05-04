import io
import os
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services.auth import get_current_user
from app.services import vision
from app.core.config import settings
import cv2

router = APIRouter(prefix="/api/labels", tags=["labels"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
ALLOWED_EXTENSIONS_WITH_PDF = ALLOWED_EXTENSIONS | {".pdf"}


def _pdf_to_png_bytes(pdf_bytes: bytes) -> bytes:
    """Extrae la primera página del PDF y la devuelve como PNG en memoria."""
    import fitz  # PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if doc.page_count == 0:
        raise HTTPException(status_code=400, detail="El PDF no contiene páginas")
    page = doc.load_page(0)
    # Renderizar a 150 DPI para equilibrio entre calidad y tamaño
    mat = fitz.Matrix(150 / 72, 150 / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")


def _save_upload(file: UploadFile, project_id: int) -> str:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS_WITH_PDF:
        raise HTTPException(status_code=400, detail=f"Formato no permitido: {ext}")
    content = file.file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande")

    if ext == ".pdf":
        # Convertir primera página a PNG
        content = _pdf_to_png_bytes(content)
        ext = ".png"

    filename = f"{uuid.uuid4()}{ext}"
    dest = os.path.join(settings.UPLOAD_DIR, filename)
    with open(dest, "wb") as f:
        f.write(content)
    return dest


@router.post("/{project_id}/upload", response_model=schemas.LabelVersionOut, status_code=201)
def upload_label(
    project_id: int,
    step: str = Form(...),
    notes: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    try:
        step_enum = models.LabelStep[step.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Paso inválido: {step}")

    existing = db.query(models.LabelVersion).filter(
        models.LabelVersion.project_id == project_id,
        models.LabelVersion.step == step_enum,
    ).first()

    image_path = _save_upload(file, project_id)

    if existing:
        # Eliminar archivos físicos anteriores
        for old_path in [existing.image_path, existing.annotated_image_path]:
            if old_path and os.path.exists(old_path):
                os.remove(old_path)
        # Eliminar comparaciones asociadas (en cascada por SQLAlchemy)
        db.query(models.Comparison).filter(
            models.Comparison.revised_version_id == existing.id
        ).delete(synchronize_session=False)
        # Si era la base (DISEÑO), eliminar también comparaciones donde es base
        if step_enum == models.LabelStep.DISENO:
            db.query(models.Comparison).filter(
                models.Comparison.base_version_id == existing.id
            ).delete(synchronize_session=False)

        existing.image_path = image_path
        existing.annotated_image_path = None
        existing.notes = notes
        existing.uploaded_by_id = current_user.id
        existing.uploaded_at = datetime.utcnow()
        label = existing
    else:
        label = models.LabelVersion(
            step=step_enum,
            image_path=image_path,
            notes=notes,
            project_id=project_id,
            uploaded_by_id=current_user.id,
        )
        db.add(label)

    # Resetear estado del proyecto según el paso reemplazado
    if step_enum == models.LabelStep.DISENO:
        project.status = models.ProjectStatus.BORRADOR
    elif step_enum == models.LabelStep.REDISENO:
        project.status = models.ProjectStatus.EN_REVISION_REDISENO
    elif step_enum == models.LabelStep.MUESTRA_IMPRENTA:
        project.status = models.ProjectStatus.EN_REVISION_IMPRENTA

    db.commit()
    db.refresh(label)
    return label


@router.get("/{project_id}/versions", response_model=List[schemas.LabelVersionOut])
def list_versions(
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
    return project.label_versions


@router.post("/{project_id}/compare/{revised_version_id}", response_model=schemas.ComparisonOut)
def compare_labels(
    project_id: int,
    revised_version_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    base_version = db.query(models.LabelVersion).filter(
        models.LabelVersion.project_id == project_id,
        models.LabelVersion.step == models.LabelStep.DISENO,
    ).first()
    if not base_version:
        raise HTTPException(status_code=404, detail="No hay etiqueta base (DISEÑO) cargada")

    revised_version = db.query(models.LabelVersion).filter(
        models.LabelVersion.id == revised_version_id,
        models.LabelVersion.project_id == project_id,
    ).first()
    if not revised_version:
        raise HTTPException(status_code=404, detail="Versión revisada no encontrada")

    if revised_version.step == models.LabelStep.DISENO:
        raise HTTPException(status_code=400, detail="No se puede comparar el diseño base consigo mismo")

    # Ejecutar comparación
    try:
        result = vision.compare_labels(base_version.image_path, revised_version.image_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al comparar imágenes: {str(e)}")

    # Guardar imagen anotada
    annotated_path = revised_version.image_path.replace(".", "_annotated.")
    cv2.imwrite(annotated_path, result["annotated_image"])
    revised_version.annotated_image_path = annotated_path

    # Crear comparación
    comparison = models.Comparison(
        base_version_id=base_version.id,
        revised_version_id=revised_version.id,
        similarity_score=result["ssim_score"],
        color_score=result["color_score"],
        ocr_score=result["ocr_score"],
    )
    db.add(comparison)
    db.flush()

    # Guardar diferencias
    for diff in result["differences"]:
        x, y, w, h = diff["bbox"]
        difference = models.Difference(
            comparison_id=comparison.id,
            difference_type=models.DifferenceType[diff["type"]],
            description=diff["description"],
            bbox_x=x, bbox_y=y, bbox_w=w, bbox_h=h,
            severity=diff.get("severity", "MEDIA"),
            extra_data=diff.get("extra"),
        )
        db.add(difference)

    db.commit()
    db.refresh(comparison)
    return comparison


@router.patch("/comparisons/{comparison_id}/review", response_model=schemas.ComparisonOut)
def review_comparison(
    comparison_id: int,
    data: schemas.ComparisonReview,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    comparison = db.query(models.Comparison).filter(models.Comparison.id == comparison_id).first()
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparación no encontrada")

    project = db.query(models.Project).filter(
        models.Project.id == comparison.revised_version.project_id,
        models.Project.owner_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=403, detail="Sin permisos")

    comparison.status = data.status
    comparison.reviewer_notes = data.reviewer_notes

    # Actualizar estado del proyecto si fue aprobado en paso 3
    step = comparison.revised_version.step
    if data.status == models.ComparisonStatus.APROBADO:
        if step == models.LabelStep.MUESTRA_IMPRENTA:
            project.status = models.ProjectStatus.VERIFICADA
    elif data.status == models.ComparisonStatus.RECHAZADO:
        project.status = models.ProjectStatus.RECHAZADA

    db.commit()
    db.refresh(comparison)
    return comparison


@router.get("/image/{version_id}/annotated")
def get_annotated_image(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    version = db.query(models.LabelVersion).filter(models.LabelVersion.id == version_id).first()
    if not version or not version.annotated_image_path:
        raise HTTPException(status_code=404, detail="Imagen anotada no disponible")
    return FileResponse(version.annotated_image_path)


@router.get("/image/{version_id}/original")
def get_original_image(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    version = db.query(models.LabelVersion).filter(models.LabelVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    return FileResponse(version.image_path)
