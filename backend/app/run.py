import os
import uvicorn

if __name__ == "__main__":
    # Lee el puerto de Railway. Si no existe, usa el 8000 por defecto.
    port = int(os.getenv("PORT", 8000))
    
    # Arranca Uvicorn pasando el puerto como un entero limpio de Python
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=port, 
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
