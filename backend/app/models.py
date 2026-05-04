import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Enum as SAEnum, Float, Boolean, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


# ─── Enumeraciones ───────────────────────────────────────────────────────────

class ProjectStatus(str, enum.Enum):
    BORRADOR = "BORRADOR"                          # Creado, sin etiqueta base
    EN_REVISION_REDISENO = "EN_REVISION_REDISENO"  # Paso 2 subido, pendiente verificación
    EN_REVISION_IMPRENTA = "EN_REVISION_IMPRENTA"  # Paso 3 subido, pendiente verificación
    VERIFICADA = "VERIFICADA"                       # Aprobada en los 3 pasos
    RECHAZADA = "RECHAZADA"                         # Rechazada en algún punto


class LabelStep(str, enum.Enum):
    DISENO = "DISENO"              # Paso 1: diseño base
    REDISENO = "REDISENO"          # Paso 2: retoque por diseñador
    MUESTRA_IMPRENTA = "MUESTRA_IMPRENTA"  # Paso 3: retoque de imprenta


class DifferenceType(str, enum.Enum):
    TEXTO = "TEXTO"
    COLOR = "COLOR"
    FORMA = "FORMA"
    ELEMENTO_FALTANTE = "ELEMENTO_FALTANTE"
    ELEMENTO_EXTRA = "ELEMENTO_EXTRA"
    GENERAL = "GENERAL"


class ComparisonStatus(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"


# ─── Modelos ─────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="owner")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    product_name = Column(String(255), nullable=True)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.BORRADOR, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="projects")

    label_versions = relationship("LabelVersion", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="project", cascade="all, delete-orphan")


class LabelVersion(Base):
    __tablename__ = "label_versions"

    id = Column(Integer, primary_key=True, index=True)
    step = Column(SAEnum(LabelStep), nullable=False)
    image_path = Column(String(500), nullable=False)
    annotated_image_path = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="label_versions")

    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploader = relationship("User", foreign_keys=[uploaded_by_id])

    # Comparaciones donde esta versión es la "revisada" (paso 2 o 3)
    comparisons = relationship(
        "Comparison",
        foreign_keys="Comparison.revised_version_id",
        back_populates="revised_version",
        cascade="all, delete-orphan",
    )


class Comparison(Base):
    __tablename__ = "comparisons"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(SAEnum(ComparisonStatus), default=ComparisonStatus.PENDIENTE)
    similarity_score = Column(Float, nullable=True)   # 0.0 – 1.0
    ocr_score = Column(Float, nullable=True)           # similitud de texto
    color_score = Column(Float, nullable=True)
    compared_at = Column(DateTime, default=datetime.utcnow)
    reviewer_notes = Column(Text, nullable=True)

    # La versión base siempre es DISEÑO (paso 1)
    base_version_id = Column(Integer, ForeignKey("label_versions.id"), nullable=False)
    base_version = relationship("LabelVersion", foreign_keys=[base_version_id])

    revised_version_id = Column(Integer, ForeignKey("label_versions.id"), nullable=False)
    revised_version = relationship(
        "LabelVersion",
        foreign_keys=[revised_version_id],
        back_populates="comparisons",
    )

    differences = relationship("Difference", back_populates="comparison", cascade="all, delete-orphan")


class Difference(Base):
    __tablename__ = "differences"

    id = Column(Integer, primary_key=True, index=True)
    difference_type = Column(SAEnum(DifferenceType), nullable=False)
    description = Column(Text, nullable=False)

    # Coordenadas del bounding box en la imagen revisada (px)
    bbox_x = Column(Integer, nullable=True)
    bbox_y = Column(Integer, nullable=True)
    bbox_w = Column(Integer, nullable=True)
    bbox_h = Column(Integer, nullable=True)

    severity = Column(String(20), default="MEDIA")  # BAJA | MEDIA | ALTA
    extra_data = Column(JSON, nullable=True)          # Datos adicionales (texto encontrado, etc.)

    comparison_id = Column(Integer, ForeignKey("comparisons.id"), nullable=False)
    comparison = relationship("Comparison", back_populates="differences")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String(500), nullable=True)   # PDF exportado

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="reports")

    comparison_id = Column(Integer, ForeignKey("comparisons.id"), nullable=True)
    comparison = relationship("Comparison")
