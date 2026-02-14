# 🚀 OSRS Trading - Arquitectura Completa

## 📐 Arquitectura: Backend + Frontend Separados

```
┌─────────────────────────────────────────────────────┐
│  BACKEND (tu Mac / VPS)                             │
│  - Ejecuta pipelines pesados                        │
│  - Procesa 4,500 items                              │
│  - Genera candidatos finales                        │
│  - Sube resultados a GitHub                         │
└─────────────────────────────────────────────────────┘
                      ↓ ↑
              GitHub (Storage)
                      ↓ ↑
┌─────────────────────────────────────────────────────┐
│  FRONTEND (Streamlit Cloud)                         │
│  - Dashboard interactivo                            │
│  - Solo lee datos de GitHub                         │
│  - Usuarios: tú + amigos                            │
│  - GRATIS, siempre online                           │
└─────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo Dinámico de Usuario

### Caso 1: Usuario cambia configuración

```
1. Usuario en Streamlit:
   - Cambia capital a 50M GP
   - Cambia perfil a "aggressive"
   - Click "Save & Request Backend Update"

2. Streamlit:
   - Guarda config.yaml
   - Crea user_requests.json con request pendiente
   - Commit + push a GitHub

3. Backend (auto-sync cada 3 días):
   - Pull de GitHub
   - Detecta user_requests.json con status="pending"
   - Lee nuevo config.yaml
   - Re-ejecuta pipeline con nuevos filtros
   - Genera nuevos candidatos
   - Push resultados a GitHub
   - Marca request como "completed"

4. Streamlit Cloud:
   - Auto-redeploy (~30 seg)
   - Usuario ve nuevos candidatos
```

---

## 📁 Estructura de Archivos en GitHub

```
Repo GitHub:
├── app.py                          # Streamlit main
├── pages/                          # Páginas dashboard
├── scripts/
│   ├── run_pipeline.py             # Pipeline master
│   └── auto_sync.py                # ← NUEVO: Backend automation
├── data/
│   ├── processed/
│   │   ├── final_candidates_*.parquet  # ← SÍ subir
│   │   └── metadata.json               # ← SÍ subir
│   └── raw/                        # ← NO subir (en .gitignore)
├── .streamlit/
│   ├── config.toml
│   └── user_requests.json          # ← SÍ subir (comunicación)
└── config.yaml                     # ← SÍ subir (editable por usuario)
```

---

## 🛠️ OPCIÓN 1: Backend en tu Mac

### Setup:

```bash
cd /Users/jesusfusterbarroso/Desktop/osrs_moneymaking

# Copiar script de auto-sync
cp auto_sync.py scripts/

# Hacer ejecutable
chmod +x scripts/auto_sync.py

# Configurar cron (ejecutar cada 3 días a las 6 AM)
crontab -e

# Agregar línea:
0 6 */3 * * cd /Users/jesusfusterbarroso/Desktop/osrs_moneymaking && .venv/bin/python scripts/auto_sync.py >> data/logs/auto_sync.log 2>&1
```

### Ventajas:
- ✅ GRATIS
- ✅ Usa tu hardware
- ✅ Control total

### Desventajas:
- ⚠️ Tu Mac debe estar encendido
- ⚠️ No funciona si está dormido/apagado

---

## 🛠️ OPCIÓN 2: Backend en VPS (RECOMENDADO)

### Proveedores baratos:
- **Hetzner:** ~4€/mes
- **DigitalOcean:** ~6$/mes
- **Vultr:** ~5$/mes

### Setup en VPS Ubuntu:

```bash
# 1. Conectar por SSH
ssh root@tu-vps-ip

# 2. Instalar dependencias
apt update
apt install python3-pip git

# 3. Clonar repo
git clone https://github.com/TU_USUARIO/osrs-trading-dashboard.git
cd osrs-trading-dashboard

# 4. Setup Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 5. Configurar Git (para poder hacer push)
git config user.name "Auto Backend"
git config user.email "backend@example.com"
git config credential.helper store
git push  # Te pedirá usuario/password una vez, luego se guarda

# 6. Configurar cron
crontab -e

# Agregar:
0 6 */3 * * cd /root/osrs-trading-dashboard && /root/osrs-trading-dashboard/.venv/bin/python scripts/auto_sync.py >> data/logs/auto_sync.log 2>&1

# 7. Test manual
python scripts/auto_sync.py
```

### Ventajas:
- ✅ 24/7 online
- ✅ No depende de tu Mac
- ✅ Barato (~5€/mes)
- ✅ Confiable

---

## 🚀 Deploy a Streamlit Cloud

### 1. Preparar Repo

```bash
# En tu Mac:
cd /Users/jesusfusterbarroso/Desktop/osrs_moneymaking

# Asegurarse de tener .gitignore correcto
cp .gitignore_new .gitignore

# Asegurarse de que processed data se suba
git add -f data/processed/*.parquet
git add -f data/processed/metadata.json

# Commit
git add .
git commit -m "Ready for deployment"
git push
```

### 2. Deploy en Streamlit Cloud

1. Ir a [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. New app:
   - Repo: `osrs-trading-dashboard`
   - Branch: `main`
   - Main file: `app.py`
4. Deploy!

### 3. Configurar Secrets (Opcional)

En Streamlit Cloud → Settings → Secrets:

```toml
password = "tu-password-aqui"
```

---

## 📊 Workflow Completo

### Primera vez (Setup):

```bash
# Backend (tu Mac o VPS):
1. git clone repo
2. python scripts/run_bulk_download.py          # Una sola vez, ~90 min
3. python scripts/run_pipeline.py --mode full --reanalyze  # ~90 min
4. python scripts/auto_sync.py                  # Sube resultados
5. Configurar cron

# Frontend:
6. Deploy en Streamlit Cloud
7. Compartir URL con amigos
```

### Uso diario:

```
1. Usuario entra a dashboard
2. Ve candidatos actuales
3. (Opcional) Cambia configuración
4. Click "Save & Request Backend Update"
5. Backend detecta request (máx 3 días después)
6. Re-ejecuta pipeline con nuevo config
7. Usuario ve nuevos candidatos (~30 seg después del push)
```

### Actualizaciones regulares (automáticas):

```
Cada 3 días:
- Cron ejecuta auto_sync.py
- Pull de GitHub
- Ejecuta pipeline incremental (~13 min)
- Push resultados
- Streamlit auto-actualiza
```

---

## 🔐 Seguridad

### Tokens de GitHub:

Para que backend pueda hacer push automático:

```bash
# 1. Crear Personal Access Token en GitHub:
# GitHub → Settings → Developer Settings → Personal Access Tokens
# Permisos: repo (full control)

# 2. Usar token en vez de password:
git remote set-url origin https://TU_TOKEN@github.com/TU_USUARIO/osrs-trading-dashboard.git

# O configurar credential helper:
git config credential.helper store
git push  # Introduce username + token (se guarda)
```

---

## 📊 Monitoreo

### Ver logs del backend:

```bash
# En tu Mac / VPS:
tail -f data/logs/auto_sync.log

# Ver últimas 100 líneas:
tail -100 data/logs/auto_sync.log
```

### Ver status en Streamlit:

Ve a la página "Run Pipeline" → Tab "Status"

---

## 🐛 Troubleshooting

**Backend no se ejecuta:**
```bash
# Verificar cron está activo:
crontab -l

# Test manual:
python scripts/auto_sync.py

# Ver logs:
cat data/logs/auto_sync.log
```

**Git push falla:**
```bash
# Verificar credenciales:
git config credential.helper store
git pull  # Te pedirá credenciales
```

**Streamlit no ve datos nuevos:**
```bash
# Verificar que se subieron:
git log -1  # Ver último commit
git ls-files data/processed/  # Ver archivos trackeados

# Forzar redeploy en Streamlit Cloud:
# Ir a dashboard → Reboot app
```

---

## 💡 Mejores Prácticas

1. **Backend siempre encendido** (VPS recomendado)
2. **Backups regulares** del repo
3. **Monitorear logs** semanalmente
4. **Documentar cambios** en commits
5. **No commitear datos RAW** (muy pesado)

---

## 🎯 Resumen

| Componente | Dónde | Qué hace | Costo |
|------------|-------|----------|-------|
| **Backend** | Tu Mac / VPS | Ejecuta pipelines | Gratis / 5€/mes |
| **Storage** | GitHub | Guarda código + resultados | Gratis |
| **Frontend** | Streamlit Cloud | Dashboard visual | Gratis |

**Total: 0-5€/mes para sistema completo 24/7** 🎉

---

Made with ❤️ for OSRS traders
