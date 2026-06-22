"""
Servicio de visión por computadora para comparar etiquetas de packaging.

Pipeline robusto orientado a minimizar falsos positivos en archivos de
preimpresión (1-20 MB), mediante:

  1. Alineación previa (Image Registration) con ECC y respaldo ORB+RANSAC.
  2. Filtrado morfológico (OPEN -> CLOSE) del mapa de diferencias SSIM.
  3. Escalado dinámico de umbrales de área en función de los megapíxeles.
  4. Comparación de texto por similitud de cadenas (difflib.SequenceMatcher)
     con normalización de espaciado (tracking/kerning), en lugar de comparar
     posiciones exactas de bounding boxes.

Todas las fases reciben sus parámetros desde `CompareConfig`, de modo que la
afinación se haga por configuración y no editando el cuerpo de las funciones.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pytesseract
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger(__name__)

BBox = Tuple[int, int, int, int]  # (x, y, w, h)


# ─── Configuración (parámetros optimizables) ─────────────────────────────────

@dataclass
class CompareConfig:
    """Parámetros del pipeline. Ajustar acá en lugar de tocar las funciones."""

    # --- Alineación (registration) ---
    align_max_dim: int = 1200          # se estima el warp en una versión reducida (perf + robustez)
    ecc_iterations: int = 1000
    ecc_eps: float = 1e-6
    ecc_gauss_filt: int = 5            # suavizado interno de ECC (atenúa anti-aliasing)
    orb_features: int = 5000
    orb_ratio: float = 0.75           # ratio test de Lowe
    orb_min_matches: int = 12

    # --- SSIM (estructura) ---
    # NO se usa un gate global de score: un cambio local real (un dígito, un
    # logo) casi no mueve el SSIM global, así que un gate que limpie el ruido
    # también escondería el defecto. La supresión de falsos positivos recae en
    # la alineación + morfología (kernel chico) + área mínima dinámica.
    ssim_diff_threshold: int = 110     # binarización del mapa de diferencias (0-255)

    # --- Color (HSV) ---
    color_hue_threshold: int = 45      # diferencia mínima de matiz (0-180, circular)
    color_min_saturation: int = 50     # ignora zonas casi grises (hue poco fiable)

    # --- Escalado dinámico de área ---
    # min_area = (ancho * alto) / divisor, acotado por [area_floor, ...].
    # divisor 20000 ~= 125 px² en 2.5 MP: chico a propósito, porque los cambios
    # reales de etiqueta (un dígito, una palabra) son regiones de ~100-350 px².
    # Lo que separa ruido de cambio real es el OPEN morfológico, no el área.
    ssim_area_divisor: float = 20000.0
    color_area_divisor: float = 20000.0
    area_floor: int = 80

    # --- Morfología del mapa de diferencias ---
    # kernel CHICO (3): el OPEN elimina motas de 1-2 px (anti-aliasing/JPEG) pero
    # conserva los trazos finos del texto. Un kernel 7 borraba el 80% de los
    # píxeles de un cambio real de texto => no detectaba nada.
    morph_kernel: int = 3

    # --- OCR ---
    # En exports de baja resolución (~1 MP) Tesseract es inestable: una misma
    # etiqueta leída dos veces difiere ~50%, lo que genera falsos positivos de
    # texto. Por eso el reporte de diferencias de texto está APAGADO por defecto;
    # un cambio de texto real igual se detecta como FORMA (mueve píxeles).
    # Activá `ocr_report_diffs` sólo con material de alta resolución (>4-5 MP).
    ocr_lang: str = "spa+eng"
    ocr_min_conf: int = 65             # confianza mínima de pytesseract (0-100)
    ocr_report_diffs: bool = False     # emitir diferencias de TEXTO (no sólo el score)
    ocr_similarity_gate: float = 0.92  # >=92% de coincidencia global => ignorar micro-variaciones


# Configuración por defecto reutilizable.
DEFAULT_CONFIG = CompareConfig()

DiffResult = Dict[str, Any]


# ─── Utilidades de carga ─────────────────────────────────────────────────────

def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"No se pudo cargar la imagen: {path}")
    return img


def resize_to_match(img1: np.ndarray, img2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Redimensiona img2 al tamaño de img1 si difieren (paso previo a la alineación fina)."""
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]
    if (h1, w1) != (h2, w2):
        img2 = cv2.resize(img2, (w1, h1), interpolation=cv2.INTER_AREA)
    return img1, img2


def _to_gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img


def dynamic_min_area(shape: Tuple[int, ...], divisor: float, floor: int) -> int:
    """
    Calcula el área mínima de un contorno como proporción del área total.

    Reemplaza los umbrales fijos (p.ej. 400 px²) que fallan según la resolución:
    una mancha de 400 px² es ruido en una imagen de 20 MP pero un cambio real en
    una de 1 MP. Escala linealmente con los megapíxeles de la entrada.
    """
    h, w = shape[:2]
    return max(floor, int((h * w) / divisor))


# ─── FASE 1: Alineación previa (Image Registration) ──────────────────────────

def _estimate_ecc(ref_gray: np.ndarray, tgt_gray: np.ndarray,
                  cfg: CompareConfig) -> Optional[np.ndarray]:
    """
    Estima una transformación euclídea (rotación + traslación) sub-pixel con ECC.

    Devuelve la matriz afín 2x3 que mapea `ref` -> `tgt`, o None si no converge.
    """
    warp = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
                cfg.ecc_iterations, cfg.ecc_eps)
    try:
        _cc, warp = cv2.findTransformECC(
            ref_gray, tgt_gray, warp, cv2.MOTION_EUCLIDEAN,
            criteria, None, cfg.ecc_gauss_filt,
        )
        return warp
    except cv2.error as e:
        logger.info("ECC no convergió (%s); se intentará alineación por características.", e)
        return None


def _estimate_orb(ref_gray: np.ndarray, tgt_gray: np.ndarray,
                  cfg: CompareConfig) -> Optional[np.ndarray]:
    """
    Estima una transformación de similitud (rotación + escala + traslación) por
    características ORB + RANSAC. Robusto cuando las dimensiones o el encuadre
    difieren más de lo que ECC puede resolver.

    Devuelve la matriz afín 2x3 que mapea `ref` -> `tgt`, o None si falla.
    """
    orb = cv2.ORB_create(cfg.orb_features)
    kp_ref, des_ref = orb.detectAndCompute(ref_gray, None)
    kp_tgt, des_tgt = orb.detectAndCompute(tgt_gray, None)
    if des_ref is None or des_tgt is None:
        return None

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    knn = matcher.knnMatch(des_ref, des_tgt, k=2)
    good = [m for pair in knn if len(pair) == 2
            for m, n in [pair] if m.distance < cfg.orb_ratio * n.distance]
    if len(good) < cfg.orb_min_matches:
        logger.info("ORB: matches insuficientes (%d).", len(good))
        return None

    src = np.float32([kp_ref[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_tgt[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    matrix, _inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC)
    return matrix


def align_images(reference: np.ndarray, target: np.ndarray,
                 cfg: CompareConfig = DEFAULT_CONFIG) -> np.ndarray:
    """
    Solapa `target` sobre `reference` a nivel sub-pixel.

    Estrategia:
      - Estima el warp en una versión reducida (más rápido y estable en 20 MP).
      - Intenta ECC (euclídeo) primero; si no converge, ORB + RANSAC.
      - Aplica el warp a resolución completa.
      - Rellena las zonas sin información (bordes tras la rotación) con los
        píxeles de `reference`, de modo que NO generen diferencias espurias.

    Si todo falla, devuelve `target` sin alterar (ya redimensionado al exterior).
    """
    h, w = reference.shape[:2]
    ref_gray = _to_gray(reference)
    tgt_gray = _to_gray(target)

    # Escala de estimación: trabajamos sobre una versión reducida y luego
    # reescalamos la traslación de la matriz a resolución completa.
    scale = max(h, w) / float(cfg.align_max_dim)
    if scale > 1.0:
        small = (int(w / scale), int(h / scale))
        ref_small = cv2.resize(ref_gray, small, interpolation=cv2.INTER_AREA)
        tgt_small = cv2.resize(tgt_gray, small, interpolation=cv2.INTER_AREA)
    else:
        scale = 1.0
        ref_small, tgt_small = ref_gray, tgt_gray

    matrix = _estimate_ecc(ref_small, tgt_small, cfg)
    if matrix is None:
        matrix = _estimate_orb(ref_small, tgt_small, cfg)
    if matrix is None:
        logger.warning("Alineación fallida; se usa el target sin registrar.")
        return target

    # Reescalar la traslación al tamaño completo (rotación/escala no cambian).
    matrix = matrix.copy()
    matrix[:, 2] *= scale

    aligned = cv2.warpAffine(
        target, matrix, (w, h),
        flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    )
    # Máscara de píxeles realmente cubiertos por el warp.
    valid = cv2.warpAffine(
        np.full((h, w), 255, np.uint8), matrix, (w, h),
        flags=cv2.INTER_NEAREST + cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    )
    invalid = valid == 0
    if invalid.any():
        aligned[invalid] = reference[invalid]
    return aligned


# ─── FASE 2: Limpieza morfológica del mapa de diferencias ────────────────────

def _clean_diff_mask(mask: np.ndarray, kernel_size: int) -> np.ndarray:
    """
    Disuelve píxeles aislados y ruido de anti-aliasing con OPEN seguido de CLOSE.

    OPEN  -> elimina motas sueltas (artefactos de compresión, bordes de letras).
    CLOSE -> reconecta una región real fragmentada por el OPEN.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    return closed


def _boxes_from_mask(mask: np.ndarray, min_area: int) -> List[BBox]:
    """Devuelve bounding boxes de los contornos cuya área supera `min_area`."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: List[BBox] = []
    for cnt in contours:
        if cv2.contourArea(cnt) > min_area:
            boxes.append(cv2.boundingRect(cnt))
    return boxes


# ─── FASE 3 (parte SSIM): comparación estructural ────────────────────────────

def compute_ssim(img1: np.ndarray, img2: np.ndarray) -> Tuple[float, np.ndarray]:
    """Retorna (score, diff_map uint8) donde diff_map ~255 = igual, ~0 = distinto."""
    gray1 = _to_gray(img1)
    gray2 = _to_gray(img2)
    score, diff = ssim(gray1, gray2, full=True)
    diff = (diff * 255).astype(np.uint8)
    return float(score), diff


def find_difference_regions(diff: np.ndarray, cfg: CompareConfig = DEFAULT_CONFIG) -> List[BBox]:
    """
    Binariza el mapa de diferencias, lo limpia morfológicamente y extrae las
    regiones cuyo área supera el umbral dinámico.
    """
    _, thresh = cv2.threshold(diff, cfg.ssim_diff_threshold, 255, cv2.THRESH_BINARY_INV)
    cleaned = _clean_diff_mask(thresh, cfg.morph_kernel)
    min_area = dynamic_min_area(diff.shape, cfg.ssim_area_divisor, cfg.area_floor)
    return _boxes_from_mask(cleaned, min_area)


# ─── FASE 3 (parte Color): comparación cromática ─────────────────────────────

def compute_color_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """Compara histogramas HSV (correlación media de los 3 canales). 0-1."""
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
    scores = []
    for ch in range(3):
        h1 = cv2.calcHist([hsv1], [ch], None, [64], [0, 256])
        h2 = cv2.calcHist([hsv2], [ch], None, [64], [0, 256])
        cv2.normalize(h1, h1)
        cv2.normalize(h2, h2)
        scores.append(cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL))
    return float(np.mean(scores))


def detect_color_differences(img1: np.ndarray, img2: np.ndarray,
                             cfg: CompareConfig = DEFAULT_CONFIG) -> List[BBox]:
    """
    Detecta regiones con diferencia de matiz significativa.

    Mejoras frente a la versión naïve:
      - Distancia de matiz CIRCULAR (0 y 180 son ambos rojo) para no inventar
        diferencias en los extremos del canal Hue.
      - Se ignoran píxeles de baja saturación en ambas imágenes (grises/negros):
        ahí el matiz es ruido, típico de cruces de registro y barras CMYK.
      - Limpieza morfológica + área dinámica, igual que en SSIM.
    """
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)

    h1 = hsv1[:, :, 0].astype(np.int16)
    h2 = hsv2[:, :, 0].astype(np.int16)
    hue_diff = np.abs(h1 - h2)
    hue_diff = np.minimum(hue_diff, 180 - hue_diff)  # circular

    saturated = (hsv1[:, :, 1] > cfg.color_min_saturation) & \
                (hsv2[:, :, 1] > cfg.color_min_saturation)
    mask = ((hue_diff > cfg.color_hue_threshold) & saturated).astype(np.uint8) * 255

    cleaned = _clean_diff_mask(mask, cfg.morph_kernel)
    min_area = dynamic_min_area(img1.shape, cfg.color_area_divisor, cfg.area_floor)
    return _boxes_from_mask(cleaned, min_area)


# ─── FASE 4: OCR por similitud de cadenas ────────────────────────────────────

def normalize_text(text: str) -> str:
    """
    Normaliza un string para comparación robusta:
      - colapsa cualquier secuencia de espacios en blanco a un único espacio
        (anula el efecto del tracking/kerning que mete espacios fantasma);
      - recorta extremos.
    """
    return re.sub(r"\s+", " ", text).strip()


def _ocr_lines(img: np.ndarray, cfg: CompareConfig) -> List[Dict[str, Any]]:
    """
    Extrae el texto agrupado por LÍNEA (no por palabra suelta), con su bounding
    box. Agrupar por línea da una unidad estable para comparar contenido y, a la
    vez, conserva una caja para anotar la imagen.
    """
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    data = pytesseract.image_to_data(
        rgb, output_type=pytesseract.Output.DICT, lang=cfg.ocr_lang,
    )
    lines: Dict[Tuple[int, int, int], Dict[str, Any]] = {}
    for i in range(len(data["text"])):
        word = data["text"][i].strip()
        try:
            conf = int(float(data["conf"][i]))
        except (ValueError, TypeError):
            conf = -1
        if not word or conf < cfg.ocr_min_conf:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        x, y = data["left"][i], data["top"][i]
        w, h = data["width"][i], data["height"][i]
        if key not in lines:
            lines[key] = {"words": [], "x1": x, "y1": y, "x2": x + w, "y2": y + h}
        ln = lines[key]
        ln["words"].append(word)
        ln["x1"], ln["y1"] = min(ln["x1"], x), min(ln["y1"], y)
        ln["x2"], ln["y2"] = max(ln["x2"], x + w), max(ln["y2"], y + h)

    result = []
    for ln in lines.values():
        text = normalize_text(" ".join(ln["words"]))
        if text:
            result.append({
                "text": text,
                "bbox": (ln["x1"], ln["y1"], ln["x2"] - ln["x1"], ln["y2"] - ln["y1"]),
            })
    return result


def _tokenize(lines: List[Dict]) -> List[str]:
    """Extrae palabras (>=2 caracteres alfanuméricos) del texto de las líneas."""
    text = " ".join(l["text"] for l in lines).lower()
    return [t for t in re.findall(r"[a-z0-9áéíóúñ]+", text) if len(t) >= 2]


def compute_ocr_score(base_lines: List[Dict], revised_lines: List[Dict]) -> float:
    """
    Similitud global de texto (0-1) INSENSIBLE AL ORDEN: coeficiente de Dice
    sobre el multiconjunto de palabras.

    Comparar el texto concatenado con SequenceMatcher era sensible al orden: el
    OCR lee los bloques en distinta secuencia entre dos exports casi idénticos
    (y agrupa las líneas distinto), lo que penalizaba el reordenamiento y daba
    puntajes irrealmente bajos (p.ej. 17% con 49/52 palabras compartidas).
    Comparar bolsas de palabras refleja el contenido real compartido.
    """
    base_tokens = _tokenize(base_lines)
    revised_tokens = _tokenize(revised_lines)
    if not base_tokens and not revised_tokens:
        return 1.0
    if not base_tokens or not revised_tokens:
        return 0.0
    inter = sum((Counter(base_tokens) & Counter(revised_tokens)).values())
    return 2 * inter / (len(base_tokens) + len(revised_tokens))


def compare_text(base_lines: List[Dict], revised_lines: List[Dict],
                 cfg: CompareConfig = DEFAULT_CONFIG) -> List[Dict[str, Any]]:
    """
    Compara texto por CONTENIDO, no por posición.

    1. Si la coincidencia global supera `ocr_similarity_gate` (95%), se asume que
       cualquier diferencia es micro-variación de posición (tracking/kerning) y
       NO se reporta nada.
    2. En caso contrario, alinea las líneas con `SequenceMatcher` y reporta sólo
       los bloques realmente insertados, borrados o sustituidos, con su bbox.
    """
    if compute_ocr_score(base_lines, revised_lines) >= cfg.ocr_similarity_gate:
        return []

    base_norm = [l["text"].lower() for l in base_lines]
    revised_norm = [l["text"].lower() for l in revised_lines]
    matcher = SequenceMatcher(None, base_norm, revised_norm, autojunk=False)

    diffs: List[Dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in ("delete", "replace"):
            for k in range(i1, i2):
                diffs.append({
                    "type": "TEXTO",
                    "description": f"Texto faltante o modificado: '{base_lines[k]['text']}'",
                    "bbox": base_lines[k]["bbox"],
                    "severity": "ALTA",
                    "extra": {"base_text": base_lines[k]["text"], "found_in_revised": False},
                })
        if tag in ("insert", "replace"):
            for k in range(j1, j2):
                diffs.append({
                    "type": "TEXTO",
                    "description": f"Texto nuevo o alterado en revisión: '{revised_lines[k]['text']}'",
                    "bbox": revised_lines[k]["bbox"],
                    "severity": "MEDIA",
                    "extra": {"revised_text": revised_lines[k]["text"], "found_in_base": False},
                })
    return diffs


# ─── Anotación de imagen ─────────────────────────────────────────────────────

def build_annotated_image(revised_img: np.ndarray,
                          structural_boxes: List[BBox],
                          color_boxes: List[BBox],
                          text_diffs: List[Dict]) -> np.ndarray:
    """Dibuja todas las diferencias sobre la imagen revisada (ya alineada)."""
    annotated = revised_img.copy()

    for x, y, w, h in structural_boxes:                       # forma -> rojo
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(annotated, "Forma", (x, max(y - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)

    for x, y, w, h in color_boxes:                            # color -> naranja
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 140, 255), 2)
        cv2.putText(annotated, "Color", (x, max(y - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 140, 255), 1)

    for diff in text_diffs:                                   # texto -> amarillo
        x, y, w, h = diff["bbox"]
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 255), 2)
        cv2.putText(annotated, "Texto", (x, max(y - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

    return annotated


# ─── Pipeline principal ──────────────────────────────────────────────────────

def compare_labels(base_path: str, revised_path: str,
                   cfg: CompareConfig = DEFAULT_CONFIG) -> Dict[str, Any]:
    """
    Compara la etiqueta base con la revisada y devuelve scores, diferencias y la
    imagen anotada. Mantiene el contrato consumido por el router de labels.

    Orden de fases: cargar -> redimensionar -> ALINEAR -> SSIM -> Color -> OCR.
    """
    base_img = load_image(base_path)
    revised_img = load_image(revised_path)

    # Igualar dimensiones y luego registrar a nivel sub-pixel.
    base_img, revised_img = resize_to_match(base_img, revised_img)
    revised_img = align_images(base_img, revised_img, cfg)

    # 1. SSIM (estructura)
    ssim_score, diff_map = compute_ssim(base_img, revised_img)
    structural_boxes = find_difference_regions(diff_map, cfg)

    # 2. Color
    color_score = compute_color_similarity(base_img, revised_img)
    color_boxes = detect_color_differences(base_img, revised_img, cfg)

    # 3. OCR (por similitud de cadenas)
    base_lines: List[Dict] = []
    revised_lines: List[Dict] = []
    try:
        base_lines = _ocr_lines(base_img, cfg)
        revised_lines = _ocr_lines(revised_img, cfg)
    except Exception as e:  # pytesseract / binario faltante no debe romper la comparación
        logger.warning("OCR falló: %s", e)

    ocr_score = compute_ocr_score(base_lines, revised_lines)

    # 4. Lista unificada de diferencias.
    # No se aplican gates globales de score: las regiones ya vienen filtradas por
    # alineación, morfología y área mínima dinámica. Reportar todas permite
    # detectar cambios locales reales que casi no mueven el score global.
    differences: List[Dict] = []

    for x, y, w, h in structural_boxes:
        differences.append({
            "type": "FORMA",
            "description": "Diferencia estructural/visual detectada",
            "bbox": (x, y, w, h),
            "severity": "MEDIA" if ssim_score > 0.85 else "ALTA",
            "extra": None,
        })

    for x, y, w, h in color_boxes:
        differences.append({
            "type": "COLOR",
            "description": "Diferencia de color detectada",
            "bbox": (x, y, w, h),
            "severity": "MEDIA",
            "extra": None,
        })

    # OCR como diferencias sólo si se habilita explícitamente (ver CompareConfig).
    text_diffs = compare_text(base_lines, revised_lines, cfg) if cfg.ocr_report_diffs else []
    differences.extend(text_diffs)

    # 5. Imagen anotada (sobre la revisada ya alineada).
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
