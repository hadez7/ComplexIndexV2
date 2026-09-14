## Dependencias adicionales

Para procesar PDFs escaneados es necesario instalar Poppler.

### Windows

Link githun poppler:
https://github.com/oschwartz10612/poppler-windows.git

1. Descargar Poppler.
2. Extraer la carpeta.
3. Agregar la ruta de `Library\bin` al archivo `.env`:

Instalar Poppler para procesar PDFs escaneados.

Opción 1 (recomendada):
- Instalar Poppler
- Agregar Library\bin al PATH del sistema

Opción 2:
- Configurar la variable POPPLER_PATH en el archivo .env
POPPLER_PATH=C:\poppler\poppler-26.02.0\Library\bin

### Linux

sudo apt install poppler-utils

### macOS

brew install poppler