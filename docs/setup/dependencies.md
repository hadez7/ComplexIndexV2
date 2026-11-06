# Dependencias del Sistema

Para el procesamiento de documentos PDF, reconocimiento óptico de caracteres (OCR) y compilación de catálogos internacionales (`gettext`), el sistema requiere las siguientes herramientas a nivel de sistema operativo:

1. **Poppler**: Renderizado y conversión de páginas PDF a imagen para OCR.
2. **Tesseract OCR**: Motor local de extracción de texto para documentos escaneados.
3. **Gettext**: Compilación de traducciones internacionales (`.po` a `.mo`).

---

## 1. Instalación en Linux

### Fedora / RHEL / CentOS
```bash
sudo dnf install poppler-utils tesseract tesseract-langpack-spa gettext
```

### Ubuntu / Debian
```bash
sudo apt update
sudo apt install poppler-utils tesseract-ocr tesseract-ocr-spa gettext
```

### Arch Linux / Manjaro
```bash
sudo pacman -S poppler tesseract tesseract-data-spa gettext
```

---

## 2. Instalación en macOS

Usando [Homebrew](https://brew.sh/):
```bash
brew install poppler tesseract tesseract-lang gettext
```

Si es necesario, vincula gettext a tu PATH:
```bash
echo 'export PATH="/opt/homebrew/opt/gettext/bin:$PATH"' >> ~/.zshrc
```

---

## 3. Instalación en Windows

### Poppler
1. Descarga el paquete precompilado más reciente desde [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases).
2. Extrae la carpeta en una ubicación permanente (por ejemplo `C:\Program Files\poppler`).
3. Agrega la subcarpeta `Library\bin` a la variable de entorno `PATH` del sistema, o especifica su ruta en el archivo `.env`:
   ```env
   POPPLER_PATH=C:\Program Files\poppler\Library\bin
   ```

### Tesseract OCR
1. Descarga el instalador desde [UB-Mannheim tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
2. Instala e incluye el paquete de idioma español (`tessdata/spa.traineddata`).
3. Agrega la ruta de instalación al `PATH`.

---

## 4. Verificación de Instalación

Puedes verificar que las herramientas estén disponibles ejecutando:
```bash
pdftoppm -v
tesseract --version
msgfmt --version
```
