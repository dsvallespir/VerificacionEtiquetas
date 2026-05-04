"""
Servicio de generación de reportes en texto/HTML.
"""
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models import Comparison, Project


def build_report_content(project: "Project", comparison: "Comparison") -> str:
    step_label = comparison.revised_version.step.value.replace("_", " ").title()
    lines = [
        f"# Reporte de Verificación de Etiqueta",
        f"",
        f"**Proyecto:** {project.name}",
        f"**Producto:** {project.product_name or 'N/A'}",
        f"**Paso verificado:** {step_label}",
        f"**Fecha:** {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC",
        f"**Estado de comparación:** {comparison.status.value}",
        f"",
        f"## Métricas de Similitud",
        f"",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Similitud estructural (SSIM) | {_pct(comparison.similarity_score)} |",
        f"| Similitud de color | {_pct(comparison.color_score)} |",
        f"| Similitud de texto (OCR) | {_pct(comparison.ocr_score)} |",
        f"",
    ]

    if comparison.differences:
        lines += [
            f"## Diferencias Encontradas ({len(comparison.differences)})",
            f"",
        ]
        for i, diff in enumerate(comparison.differences, 1):
            bbox = ""
            if diff.bbox_x is not None:
                bbox = f"(x={diff.bbox_x}, y={diff.bbox_y}, w={diff.bbox_w}, h={diff.bbox_h})"
            lines += [
                f"### {i}. [{diff.severity}] {diff.difference_type.value}",
                f"- **Descripción:** {diff.description}",
                f"- **Ubicación:** {bbox or 'No especificada'}",
                f"",
            ]
    else:
        lines += ["## Sin diferencias detectadas ✓", ""]

    if comparison.reviewer_notes:
        lines += [f"## Notas del Revisor", f"", comparison.reviewer_notes, ""]

    return "\n".join(lines)


def _pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val * 100:.1f}%"
