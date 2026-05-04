"""
Servicio de visión por computadora para comparar etiquetas.
Usa OpenCV (SSIM) + pytesseract (OCR) para detectar diferencias.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytesseract
from skimage.metrics import structural_similarity as ssim
from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


# ─── Tipos internos ──────────────────────────────────────────────────────────

DiffResult = Dict[str, Any]


# ─── Utilidades ──────────────────────────────────────────────────────────────

def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"No se pudo cargar la imagen: {path}")
    return img


def resize_to_match(img1: np.ndarray, img2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Redimensiona img2 al tamaño de img1 si difieren."""
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]
    if (h1, w1) != (h2, w2):
        img2 = cv2.resize(img2, (w1, h1), interpolation=cv2.INTER_AREA)
    return img1, img2


# ─── Comparación estructural (SSIM) ──────────────────────────────────────────

def compute_ssim(img1: np.ndarray, img2: np.ndarray) -> Tuple[float, np.ndarray]:
    """Retorna (score, diff_map) donde diff_map es la imagen de diferencias."""
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    score, diff = ssim(gray1, gray2, full=True)
    diff = (diff * 255).astype(np.uint8)
    return float(score), diff


def find_difference_regions(diff: np.ndarray, threshold: int = 60) -> List[Tuple[int, int, int, int]]:
    """Devuelve lista de bounding boxes (x,y,w,h) donde hay diferencias."""
    _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(thresh, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 400:  # ignorar artefactos JPEG y ruido pequeño
            x, y, w, h = cv2.boundingRect(cnt)
            boxes.append((x, y, w, h))
    return boxes


# ─── Comparación de color ────────────────────────────────────────────────────

def compute_color_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """Compara histogramas de color en HSV. Retorna score 0-1."""
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
    scores = []
    for ch in range(3):
        h1 = cv2.calcHist([hsv1], [ch], None, [64], [0, 256])
        h2 = cv2.calcHist([hsv2], [ch], None, [64], [0, 256])
        cv2.normalize(h1, h1)
        cv2.normalize(h2, h2)
        score = cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL)
        scores.append(score)
    return float(np.mean(scores))


def detect_color_differences(img1: np.ndarray, img2: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detecta regiones con diferencias de color significativas."""
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
    diff = cv2.absdiff(hsv1[:, :, 0], hsv2[:, :, 0])  # Canal Hue
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    dilated = cv2.dilate(thresh, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for cnt in contours:
        if cv2.contourArea(cnt) > 600:
            boxes.append(cv2.boundingRect(cnt))
    return boxes


# ─── OCR ─────────────────────────────────────────────────────────────────────

def extract_text_regions(img: np.ndarray) -> List[Dict[str, Any]]:
    """Extrae texto con bounding boxes usando pytesseract."""
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    data = pytesseract.image_to_data(rgb, output_type=pytesseract.Output.DICT, lang="spa+eng")
    regions = []
    n = len(data["text"])
    for i in range(n):
        text = data["text"][i].strip()
        conf = int(data["conf"][i])
        if text and conf > 30:
            regions.append({
                "text": text,
                "x": data["left"][i],
                "y": data["top"][i],
                "w": data["width"][i],
                "h": data["height"][i],
                "conf": conf,
            })
    return regions


def compare_text(base_regions: List[Dict], revised_regions: List[Dict]) -> List[Dict[str, Any]]:
    """Compara texto entre la base y la revisada. Retorna diferencias."""
    base_texts = {r["text"] for r in base_regions}
    revised_texts = {r["text"] for r in revised_regions}

    diffs = []

    # Texto faltante en la revisada
    for r in base_regions:
        if r["text"] not in revised_texts:
            diffs.append({
                "type": "TEXTO",
                "description": f"Texto faltante o modificado: '{r['text']}'",
                "bbox": (r["x"], r["y"], r["w"], r["h"]),
                "severity": "ALTA",
                "extra": {"base_text": r["text"], "found_in_revised": False},
            })

    # Texto extra en la revisada
    for r in revised_regions:
        if r["text"] not in base_texts:
            diffs.append({
                "type": "TEXTO",
                "description": f"Texto nuevo o alterado en revisión: '{r['text']}'",
                "bbox": (r["x"], r["y"], r["w"], r["h"]),
                "severity": "MEDIA",
                "extra": {"revised_text": r["text"], "found_in_base": False},
            })

    return diffs


def compute_ocr_score(base_regions: List[Dict], revised_regions: List[Dict]) -> float:
    """Score simple de similitud de texto 0-1."""
    base_set = {r["text"].lower() for r in base_regions}
    revised_set = {r["text"].lower() for r in revised_regions}
    if not base_set:
        return 1.0
    intersection = base_set & revised_set
    return len(intersection) / len(base_set)


# ─── Anotación de imagen ─────────────────────────────────────────────────────

def annotate_image(
    img: np.ndarray,
    boxes: List[Tuple[int, int, int, int]],
    label: str = "",
    color: Tuple[int, int, int] = (0, 0, 255),
) -> np.ndarray:
    annotated = img.copy()
    for x, y, w, h in boxes:
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        if label:
            cv2.putText(
                annotated, label, (x, max(y - 5, 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA
            )
    return annotated


def build_annotated_image(
    revised_img: np.ndarray,
    structural_boxes: List[Tuple[int, int, int, int]],
    color_boxes: List[Tuple[int, int, int, int]],
    text_diffs: List[Dict],
) -> np.ndarray:
    """Genera imagen revisada con todas las diferencias marcadas."""
    annotated = revised_img.copy()

    # Diferencias estructurales → rojo
    for x, y, w, h in structural_boxes:
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(annotated, "Forma", (x, max(y - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)

    # Diferencias de color → naranja
    for x, y, w, h in color_boxes:
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 140, 255), 2)
        cv2.putText(annotated, "Color", (x, max(y - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 140, 255), 1)

    # Diferencias de texto → amarillo
    for diff in text_diffs:
        x, y, w, h = diff["bbox"]
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 255), 2)
        cv2.putText(annotated, "Texto", (x, max(y - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

    return annotated


# ─── Pipeline principal ──────────────────────────────────────────────────────

def compare_labels(base_path: str, revised_path: str) -> Dict[str, Any]:
    """
    Compara etiqueta base con revisada.
    Retorna dict con scores, lista de diferencias y ruta de imagen anotada.
    """
    base_img = load_image(base_path)
    revised_img = load_image(revised_path)
    base_img, revised_img = resize_to_match(base_img, revised_img)

    # 1. SSIM
    ssim_score, diff_map = compute_ssim(base_img, revised_img)
    structural_boxes = find_difference_regions(diff_map)

    # 2. Color
    color_score = compute_color_similarity(base_img, revised_img)
    color_boxes = detect_color_differences(base_img, revised_img)

    # 3. OCR
    base_text_regions = []
    revised_text_regions = []
    try:
        base_text_regions = extract_text_regions(base_img)
        revised_text_regions = extract_text_regions(revised_img)
    except Exception as e:
        logger.warning(f"OCR falló: {e}")

    ocr_score = compute_ocr_score(base_text_regions, revised_text_regions)
    text_diffs = compare_text(base_text_regions, revised_text_regions)

    # 4. Construir lista de diferencias unificada
    differences: List[Dict] = []

    # Sólo reportar diferencias estructurales si la similitud es menor al 95%
    # (evita falsos positivos por artefactos de compresión JPEG)
    if ssim_score < 0.95:
        for x, y, w, h in structural_boxes:
            differences.append({
                "type": "FORMA",
                "description": "Diferencia estructural/visual detectada",
                "bbox": (x, y, w, h),
                "severity": "MEDIA" if ssim_score > 0.85 else "ALTA",
                "extra": None,
            })

    # Sólo reportar diferencias de color si la correlación de histograma es menor al 95%
    if color_score < 0.95:
        for x, y, w, h in color_boxes:
            differences.append({
                "type": "COLOR",
                "description": "Diferencia de color detectada",
                "bbox": (x, y, w, h),
                "severity": "MEDIA",
                "extra": None,
            })

    differences.extend(text_diffs)

    # 5. Imagen anotada
    annotated = build_annotated_image(revised_img, structural_boxes, color_boxes, text_diffs)

    return {
        "ssim_score": ssim_score,
        "color_score": color_score,
        "ocr_score": ocr_score,
        "differences": differences,
        "annotated_image": annotated,
        "structural_boxes": structural_boxes,
        "color_boxes": color_boxes,
    }
