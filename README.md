# Verificación de Etiquetas

Plataforma web para verificar la consistencia de etiquetas gráficas en sus 3 etapas de producción.

## Stack tecnológico

| Capa | Tecnologías |
|------|-------------|
| Backend | Python 3.11 · FastAPI · SQLAlchemy · Pydantic v2 |
| Visión | OpenCV · scikit-image (SSIM) · pytesseract (OCR) |
| Frontend | React 18 · TypeScript · Vite · Tailwind CSS |
| Base de datos | SQLite (dev) / PostgreSQL (prod) |

## Flujo del proceso

```
Paso 1: DISEÑO (base)
    ↓
Paso 2: REDISEÑO (diseñador gráfico)  → comparar con base → aprobar/rechazar
    ↓
Paso 3: MUESTRA IMPRENTA              → comparar con base → aprobar/rechazar
    ↓
Estado: VERIFICADA ✓
```

## Estados del proyecto

| Estado | Descripción |
|--------|-------------|
| `BORRADOR` | Proyecto creado, sin etiqueta base |
| `EN_REVISION_REDISENO` | Rediseño cargado, pendiente verificación |
| `EN_REVISION_IMPRENTA` | Muestra de imprenta cargada, pendiente verificación |
| `VERIFICADA` | Aprobada en los 3 pasos |
| `RECHAZADA` | Rechazada en algún punto del proceso |

## Inicio rápido (desarrollo)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Instalar Tesseract OCR en el sistema
# Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-spa
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker Compose

```bash
docker-compose up --build
```

- Frontend: http://localhost:5173  
- Backend API: http://localhost:8000  
- Docs interactivas: http://localhost:8000/docs

## Estructura del proyecto

```
VerificacionEtiquetas/
├── backend/
│   ├── app/
│   │   ├── core/           # Configuración
│   │   ├── routers/        # Endpoints FastAPI
│   │   ├── services/       # Visión, OCR, Auth, Reportes
│   │   ├── database.py
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── schemas.py      # Pydantic schemas
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── api/            # Cliente Axios + endpoints
│       ├── components/     # Componentes reutilizables
│       ├── context/        # AuthContext
│       ├── pages/          # Páginas de la app
│       └── types/          # Tipos TypeScript
└── docker-compose.yml
```

## Detección de diferencias

El sistema detecta tres tipos de diferencias entre etiquetas:

- 🔴 **Forma/estructura** — SSIM (Structural Similarity Index) + contornos OpenCV  
- 🟠 **Color** — Comparación de histogramas HSV  
- 🟡 **Texto** — OCR con Tesseract, comparación word-by-word  

Cada diferencia se marca visualmente sobre la imagen revisada y se lista en el reporte.
