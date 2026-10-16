# Guía de entrega, revisión y compilación

Esta guía distingue los archivos que deben permanecer en el repositorio, los
auxiliares que no deben subirse y la forma de compilar el reporte sin ejecutar
el script Python que genera el Word.

## 1. Integrantes y roles

| Integrante | Rol |
|---|---|
| Gael Askary Razo Montañez | PM y apoyo general |
| Limhi Gerson López Momox | Ingeniero de datos |
| Juan Enrique Gutierrez Hernández | Científico de datos |
| Karla Yaneth Cruz Sandoval | Desarrolladora frontend |
| Arturo Huerta Maldonado | Desarrollador backend |

Los roles describen áreas de responsabilidad y no excluyen la revisión
colaborativa de todo el equipo.

## 2. Qué debe permanecer en GitHub

### Reportes y documentación

- `Documento_Tecnico_Agrotec_Amanteca_FIRA2026.docx`: versión editable.
- `Documento_Tecnico_Agrotec_Amanteca_FIRA2026.pdf`: versión visual final.
- `Documento_Tecnico_Agrotec_Amanteca_FIRA2026.tex`: fuente del PDF.
- `Documento_Tecnico_Agrotec_Amanteca_FIRA2026.md`: versión legible en GitHub.
- `BASES_CUMPLIMIENTO_AGROCEBADA.md`: requisitos y checklist de la convocatoria.
- `GUIA_DEFENSA_ORAL_AGROTEC.md`: preparación de la presentación.
- Esta guía: `GUIA_ENTREGA_Y_COMPILACION.md`.

### Aplicación, código y artefactos

- `frontend/`, incluyendo `package.json` y `src/`.
- `backend/`, incluyendo API, núcleo compartido, pruebas y dependencias.
- `ml_pipeline/models/02_train_and_export_artifacts.py`: pipeline de datos y ML.
- `backend/tests/`: pruebas de API, paridad y artefactos.
- `docs/`: build estático servido por GitHub Pages.
- `backend/artifacts/`: modelo, métricas, GeoJSON, CSV y simulador.
- `frontend/public/data/` y `docs/data/`: copias usadas por el modo estático.
- `render.yaml` y `backend/Dockerfile`: configuración reproducible opcional.

## 3. Qué no debe subirse

No deben formar parte del commit:

- `*.aux`, `*.log`, `*.out`, `*.toc`, `*.synctex.gz`: auxiliares de LaTeX.
- `__pycache__/` y `*.pyc`.
- `node_modules/` y `frontend/dist/`; el build publicado ya está en `docs/`.
- `.env`, `.env.local`, credenciales y claves.
- Rasters, shapefiles, zips y matrices pesadas originales de `data/raw/`.
- CURP, identificaciones, cuentas bancarias, constancias fiscales o cualquier
  documento personal.
- Carpetas temporales creadas por conversiones de Word o PDF.

El `.gitignore` cubre estas categorías. Antes de entregar, ejecutar:

```powershell
git status --short
git ls-files
```

## 4. Sobre `generate_word_report.py`

`ml_pipeline/models/generate_word_report.py` se conserva como fuente histórica
y reproducible del DOCX, pero **no es necesario ejecutarlo para revisar o
compilar la entrega final**. El reporte se puede usar directamente mediante:

- `Documento_Tecnico_Agrotec_Amanteca_FIRA2026.docx`
- `Documento_Tecnico_Agrotec_Amanteca_FIRA2026.pdf`
- `Documento_Tecnico_Agrotec_FIRA2026.tex`

El script no es dependencia del dashboard ni debe ejecutarse durante la
presentación. Se conserva para trazabilidad del archivo editable; si la
plataforma solo solicita productos finales, se entrega el DOCX y el PDF.

## 5. Compilar el PDF LaTeX

### Windows con MiKTeX

1. Instalar MiKTeX y activar la instalación automática de paquetes faltantes.
2. Abrir PowerShell en `D:\Agrotec\DataSet`.
3. Compilar dos veces para actualizar índice y referencias:

```powershell
Set-Location D:\Agrotec\DataSet
pdflatex -interaction=nonstopmode -halt-on-error Documento_Tecnico_Agrotec_Amanteca_FIRA2026.tex
pdflatex -interaction=nonstopmode -halt-on-error Documento_Tecnico_Agrotec_Amanteca_FIRA2026.tex
```

4. Confirmar que se creó `Documento_Tecnico_Agrotec_Amanteca_FIRA2026.pdf`.
5. Limpiar auxiliares antes del commit:

```powershell
Remove-Item *.aux,*.log,*.out,*.toc,*.synctex.gz -ErrorAction SilentlyContinue
```

El `.tex` requiere las figuras de `data/processed/figures/` y el logo de
`frontend/public/`. No mover esas rutas sin actualizar el fuente.

### Linux/macOS

```bash
cd /ruta/al/repositorio
pdflatex -interaction=nonstopmode -halt-on-error Documento_Tecnico_Agrotec_Amanteca_FIRA2026.tex
pdflatex -interaction=nonstopmode -halt-on-error Documento_Tecnico_Agrotec_Amanteca_FIRA2026.tex
rm -f *.aux *.log *.out *.toc *.synctex.gz
```

## 6. Revisar el proyecto sin regenerar el Word

### Backend

```powershell
Set-Location D:\Agrotec\DataSet
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python -W error::DeprecationWarning -W error::PendingDeprecationWarning -m pytest backend\tests -v
Set-Location backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

La API queda en `http://localhost:8000/docs`. En el entorno validado las
pruebas terminan con `9 passed`.

### Frontend

```powershell
Set-Location D:\Agrotec\DataSet\frontend
npm install
npm run dev
```

Para validar producción:

```powershell
npm run build
```

La demo pública usa el build estático de `docs/` y no necesita iniciar la API.

## 7. Checklist previo a la entrega

- [ ] DOCX y PDF abren correctamente.
- [ ] PDF compilado desde `.tex` sin errores.
- [ ] Roles y nombres de los cinco integrantes incluidos.
- [ ] Declaración de IA y prompts revisados por el equipo.
- [ ] Video de máximo cinco minutos subido y enlazado en la plataforma.
- [ ] Dashboard accesible desde un teléfono.
- [ ] No hay secretos, credenciales ni datos personales.
- [ ] `git status --short` no muestra auxiliares inesperados.
- [ ] Pruebas backend y build frontend pasan.

## 8. Qué subir a la plataforma de FIRA

Como paquete mínimo:

1. `Documento_Tecnico_Agrotec_Amanteca_FIRA2026.docx`.
2. `Documento_Tecnico_Agrotec_Amanteca_FIRA2026.pdf`, si acepta formato adicional.
3. Repositorio: <https://github.com/GalekTato/Agrotec-Amanteca>.
4. Dashboard: <https://galektato.github.io/Agrotec-Amanteca/>.
5. Video demostrativo de máximo cinco minutos.

No subir documentos de identidad, CURP, cuentas bancarias o constancias
fiscales salvo solicitud formal posterior de FIRA por su canal oficial.
