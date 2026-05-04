Actúa como un Arquitecto de Software Senior. Necesito desarrollar una plataforma que formará parte de un proceso de verificación de etiquetas.
Las etiquetas llevan 3 pasos desde su diseño hasta su impresion:
Paso 1: diseño, es la etiqueta bien elaborada y modelo base.
Paso 2: rediseño, es la etiqueta retocada por un diseñador gráfico.
Paso 3: muestra de imprenta: es la etiqueta retocada por la imprenta.

La plataforma debe verificar que en los pasos 2 y 3 la etiqueta conserve la forma, los textos (respetando mayúsculas, minúsculas, números, signos), los colores, etc. de la etiqueta 1.

Cada etiqueta representa un "proyecto" cargado por un "usuario".

Si se encuentran diferencias en las etiquetas en los pasos 2 y 3 deben ser indicados mediante algún tipo de señalización en la imagen.

El sistema debe permitir emitir un reporte de los errores en la etiqueta para ser enviados luego al diseñador/imprenta.

Si una etiqueta llega al final del proceso, es decir, pasa el punto de control 3, debe pasar al estado "VERIFICADA". Elegir los nombres de los estados restantes a conveniencia.

Stack Tecnológico:
Backend: Python con FastAPI, SQLAlchemy (o Tortoise ORM) y Pydantic. Open CV o YOLO para la aplicacion de visión por computadora. Elegir un OCR si es necesario.
Frontend: React con TypeScript, utilizando Vite y Tailwind CSS.
Objetivo del Sistema:
Tareas que requiero de ti:
Estructura del Proyecto: Define la carpeta backend/ y frontend/.
Backend:
Crea el modelo de base de datos.
Crea un Dashboard en React TS acorde a la tarea.