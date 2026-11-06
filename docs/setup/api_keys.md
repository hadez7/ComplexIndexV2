# Configuración de Variables de Entorno y API Keys

Este documento describe la configuración de las credenciales y variables de entorno necesarias para la ejecución de la plataforma **ELI (Enterprise Lex Index)**.

---

## 1. Archivo `.env`

En la raíz del proyecto, copia la plantilla `.env.example` para crear tu archivo `.env` local:

```bash
cp .env.example .env
```

### Variables principales:

| Variable | Descripción | Requerido | Ejemplo / Valor por defecto |
|---|---|---|---|
| `SECRET_KEY` | Clave criptográfica para firmas y sesiones en Django. | **Sí** | `django-insecure-...` (o cadena aleatoria) |
| `DEBUG` | Activa modo depuración (desactivar en producción). | No | `True` / `False` |
| `ALLOWED_HOSTS` | Hosts permitidos separados por comas. | No | `127.0.0.1,localhost` |
| `OPENAI_API_KEY` | Clave de API de OpenAI utilizada como respaldo para OCR de alta precisión con GPT Vision en PDFs escaneados complejos. | Opcional | `sk-proj-xxxxxxxxxxxxxxxxxxxxxx` |
| `POPPLER_PATH` | Ruta al binario de Poppler (solo si no está agregado al PATH del sistema operativo). | Opcional | `/usr/bin` o `C:\poppler\Library\bin` |

---

## 2. Obtención de `OPENAI_API_KEY` (Opcional)

Si requieres procesamiento OCR mediante visión artificial para documentos escaneados de baja legibilidad:

1. Inicia sesión en la plataforma de [OpenAI API Keys](https://platform.openai.com/api-keys).
2. Haz clic en **"Create new secret key"**.
3. Copia el token generado y pégalo en tu archivo `.env`:
   ```env
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

> **Nota:** Para el procesamiento documental estándar (PDFs de texto vectorial, ZIPs o extracción con Tesseract/PyMuPDF local), no es obligatorio contar con una API Key activa de OpenAI; el sistema funcionará de forma local y autónoma.

---

## 3. Seguridad

- **Nunca versionar el archivo `.env` en Git**. El archivo está excluido automáticamente por `.gitignore`.
- Comparte únicamente `.env.example` en el repositorio con valores genéricos o descriptivos.
- En servidores de despliegue, inyecta las variables a través del gestor de configuración o variables de entorno del sistema operativo/contenedor.
