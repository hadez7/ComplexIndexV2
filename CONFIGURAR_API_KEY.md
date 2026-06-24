# ⚙️ Configuración de API Key de OpenAI

## 🔐 Pasos para Configurar tu API Key

### 1. **Obtén tu API Key**
   - Accede a https://platform.openai.com/account/api-keys
   - Inicia sesión con tu cuenta de OpenAI
   - Haz clic en "Create new secret key"
   - Copia la clave (aparece una sola vez, guárdala en un lugar seguro)

### 2. **Agrega tu API Key al archivo `.env`**
   
   Abre el archivo `.env` en la raíz del proyecto:
   ```
   c:\Users\Rafael Lazo\Desktop\eli-ia\ELI\.env
   ```

   Reemplaza la línea:
   ```
   OPENAI_API_KEY=sk-tu-api-key-aqui
   ```
   
   Con tu API Key real:
   ```
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxx
   ```

### 3. **Guarda el archivo**
   - Presiona Ctrl+S en VS Code
   - O guarda manualmente

### 4. **Verifica que funciona**
   ```powershell
   cd "c:\Users\Rafael Lazo\Desktop\eli-ia\ELI"
   venv\Scripts\python.exe -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key cargada:' if os.getenv('OPENAI_API_KEY') else 'ERROR: API Key no encontrada')"
   ```

---

## ⚠️ Seguridad Importante

**NUNCA hagas commit del archivo `.env` a Git**

El archivo `.env` está configurado en `.gitignore`, así que Git lo ignorará automáticamente. Aun así:

✅ **Seguro:**
- Mantener `.env` en local
- Compartir solo `.env.example` en repositorio
- Cada desarrollador tiene su propio `.env`

❌ **INSEGURO:**
- Guardar API keys en código
- Subir `.env` a GitHub
- Compartir API keys por email o chat

---

## 📝 Cómo se Carga el `.env`

Cuando ejecutas Django, automáticamente:

1. **Se busca el archivo `.env`** en la raíz del proyecto
2. **Se cargan las variables** en `os.environ`
3. **Se utilizan en el código:**

   ```python
   from dotenv import load_dotenv
   import os
   
   load_dotenv()
   api_key = os.getenv('OPENAI_API_KEY')
   ```

---

## 🔄 Si Cambias tu API Key

1. Edita `.env`
2. Reemplaza el valor antiguo por el nuevo
3. No es necesario reiniciar (se carga cada vez que se ejecuta código)

---

## 🆘 Troubleshooting

**Error: "OPENAI_API_KEY no está configurada"**
- Verifica que el archivo `.env` existe en: `c:\Users\Rafael Lazo\Desktop\eli-ia\ELI\.env`
- Verifica que la línea empieza con `OPENAI_API_KEY=` (sin espacios)
- Guarda el archivo y vuelve a ejecutar

**Error: "401 Unauthorized"**
- Significa que la API key es inválida o expiró
- Genera una nueva en https://platform.openai.com/account/api-keys
- Actualiza `.env` con la nueva clave

**Error: "Rate limit exceeded"**
- Significa que usaste demasiadas llamadas en poco tiempo
- OpenAI tiene límites según tu plan
- Espera unos minutos e intenta de nuevo

---

## 💰 Costos

Recuerda que cada llamada a OpenAI tiene costo:
- GPT-5-mini entrada: $0.25 / 1M tokens
- GPT-5-mini salida: $2.00 / 1M tokens

**Tip:** Monitora tu uso en https://platform.openai.com/account/usage/overview

---

versión: 1.0  
fecha: 2026-02-27
