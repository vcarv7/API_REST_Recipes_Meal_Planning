# API REST — Recetas y Planificación de Comidas

API REST para gestionar **recetas con sus ingredientes** y **planificar comidas semanales** por usuario.
Pensada para que cualquier aplicación cliente (web, móvil, script) pueda autenticarse con **JWT**, crear su contenido y servirlo.

**Stack:** Python 3.14 · Django 6.1 · Django REST Framework 3.18 · SimpleJWT · drf-spectacular · Poetry

---

## ¿Qué puedes hacer con esta API?

- **Catálogo de recetas**: crear recetas con instrucciones, tiempo de preparación (horas) y porciones.
- **Ingredientes con cantidad**: cada receta declara sus ingredientes y cuánto usa de cada uno. El mismo ingrediente no puede repetirse dentro de una receta.
- **Planificación semanal**: cada usuario crea planes con fecha de inicio y fin automático a **+7 días**, y agenda recetas en días y comidas (**desayuno, almuerzo, cena, merienda**). Una comida puede combinar varias recetas (sopa + plato + postre).
- **Multiusuario con permisos reales**: el recetario es de **lectura pública**; escribir requiere cuenta; cada receta **solo la edita su creador**; los planes de cada usuario son **privados**.
- **Autenticación JWT completa**: registro, login, refresh con rotación de tokens, logout con blacklist.
- **Paginación uniforme** en todos los listados (sobre `count / next / previous / results`).
- **Documentación interactiva** (OpenAPI 3): Swagger UI para probar todo desde el navegador.
- **Validaciones de negocio**: fechas dentro del rango del plan, no duplicar comidas en el mismo slot, no borrar recetas en uso, no duplicar ingredientes por receta.

## Quickstart (desarrollo)

Requisitos: **Python 3.14+** y **Poetry**.

```bash
git clone https://github.com/vcarv7/API_REST_Recipes_Meal_Planning.git
cd API_REST_Recipes_Meal_Planning
poetry install
cp .env.example .env          # Windows/PowerShell: Copy-Item .env.example .env
```

Genera un `SECRET_KEY` para tu `.env`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Completa el resto de `.env` (ver tabla abajo) y arranca:

```bash
poetry run python manage.py migrate
poetry run python manage.py createsuperuser --username tuusuario
poetry run python manage.py runserver
```

| URL | Qué hay |
|-----|---------|
| http://127.0.0.1:8000/api/ | La API |
| http://127.0.0.1:8000/api/docs/ | **Swagger UI** (interactiva, con botón Authorize) |
| http://127.0.0.1:8000/health | Estado de la API (check de base de datos) |
| http://127.0.0.1:8000/admin/ | Admin de Django |

## Variables de entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `SECRET_KEY` | ✅ | Clave de Django (firma los JWT). Nunca compartirla ni commitearla |
| `DEBUG` | — | `True`/`False`. Solo afecta a desarrollo (producción la fuerza a `False`) |
| `ALLOWED_HOSTS` | — | Hosts separados por coma, ej. `localhost,127.0.0.1` |
| `DATABASE_URL` | — | URL de conexión. Default `sqlite:///db.sqlite3`. Producción: `postgres://usuario:clave@host:5432/base` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | — | Solo producción (SMTP) |

## Autenticación JWT — el flujo de un cliente

```
1. REGISTRO   POST /api/auth/register/                → 201
2. LOGIN      POST /api/auth/token/                   → {access, refresh}     ← guárdalos
3. USO        Authorization: Bearer <access>          ← en CADA request
4. EXPIRA     access vencido → 401                    ← pide refresh y reintenta
5. REFRESH    POST /api/auth/token/refresh/ {refresh} → nuevo access (el refresh rota)
6. LOGOUT     POST /api/auth/token/blacklist/ {refresh} → refresh quemado
```

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/auth/register/` | Crea usuario: `username`, `password`, `email?` (único), `country`, `date_birth` |
| POST | `/api/auth/token/` | Login → `{access, refresh}` |
| POST | `/api/auth/token/refresh/` | Nuevo access (y refresh rotado) |
| POST | `/api/auth/token/verify/` | Valida un token |
| POST | `/api/auth/token/blacklist/` | Logout: invalida el refresh |

**Ejemplos (curl):**

```bash
BASE=http://127.0.0.1:8000

# Login
curl -s -X POST $BASE/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"tuusuario","password":"tuclave"}'

# Usar el access
curl -s $BASE/api/plans/ -H "Authorization: Bearer <ACCESS>"

# Refrescar
curl -s -X POST $BASE/api/auth/token/refresh/ \
  -H "Content-Type: application/json" -d '{"refresh":"<REFRESH>"}'

# Logout
curl -s -X POST $BASE/api/auth/token/blacklist/ \
  -H "Content-Type: application/json" -d '{"refresh":"<REFRESH>"}'
```

**Lo que un cliente bien portado debe saber:**

- Access token vive **30 minutos**; refresh **7 días** (y rota en cada refresh: el anterior muere).
- `401` = no autenticado / token inválido → refresca y reintenta. `403` = autenticado sin permiso.
- Logout invalida el **refresh**, pero el access sigue válido hasta expirar — JWT es **stateless**. Mantén las vidas cortas y usa HTTPS en producción.

## Endpoints

| Recurso | Rutas | Lectura | Escritura |
|---------|-------|---------|-----------|
| Ingredientes | `/api/ingredients/` · `/api/ingredients/{id}/` | Pública | Autenticada |
| Recetas | `/api/recipes/` · `/api/recipes/{id}/` | Pública | Autenticada + **solo el creador** |
| Líneas de receta | `/api/recipes/{id}/recipe-ingredients/` · `/api/recipe-ingredients/{id}/` | Pública | Autenticada + **dueño de la receta** |
| Planes | `/api/plans/` · `/api/plans/{id}/` | **Solo el usuario** | Solo el usuario |
| Comidas del plan | `/api/plans/{id}/meals/` · `/api/plan-meals/{id}/` | Solo el usuario | Solo el usuario |

**Campos principales:**

- `Ingredient`: `{id, name, unit}`
- `Recipe`: `{id, name, instructions, prep_time, servings, created_by (solo lectura), recipe_ingredients[]}`
- Línea de receta — se **escribe** con `{ingredient_id, quantity}` y se **lee** con `{id, ingredient: {id, name, unit}, quantity}`
- `Plan`: `{id, start_date, end_date, meals[]}` — omite fechas y el servidor pone inicio = ahora y fin = inicio + 7 días
- Comida — se **escribe** con `{recipe_id, date: "AAAA-MM-DD", meal_type}` y se **lee** con `{id, recipe: {id, name, prep_time, servings}, date, meal_type}`
- `meal_type` ∈ `breakfast` · `lunch` · `dinner` · `snack`

## Ejemplo de punta a punta

```bash
BASE=http://127.0.0.1:8000
TOKEN=<ACCESS>

# 1) Ingrediente
curl -s -X POST $BASE/api/ingredients/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"name":"Huevo","unit":"unidades"}'

# 2) Receta
curl -s -X POST $BASE/api/recipes/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Tortilla","instructions":"Batir y cuajar.","prep_time":0.5,"servings":4}'

# 3) Línea de ingrediente (receta 1 + ingrediente 1)
curl -s -X POST $BASE/api/recipes/1/recipe-ingredients/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"ingredient_id":1,"quantity":4}'

# 4) Plan semanal (fin automático)
curl -s -X POST $BASE/api/plans/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{}'

# 5) Comida en el plan (usa una fecha dentro del rango start_date..end_date)
curl -s -X POST $BASE/api/plans/1/meals/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"recipe_id":1,"date":"2026-11-03","meal_type":"lunch"}'
```

## Paginación

Todos los listados responden el mismo sobre (10 elementos por página):

```json
{"count": 23, "next": ".../api/ingredients/?page=2", "previous": null, "results": [ ... ]}
```

## Rate limiting

| Scope | Límite por defecto |
|-------|--------------------|
| Anónimo | 1.000 peticiones/día |
| Usuario autenticado | 10.000 peticiones/día |
| Login (`/api/auth/token/`) | 10/min |
| Registro (`/api/auth/register/`) | 10/hora |

Al exceder el límite: `429` con header `Retry-After`. Los límites se ajustan por entorno con las variables `THROTTLE_*` (ver `.env.example`).

## Documentación interactiva

- **Swagger UI**: `/api/docs/` — pega tu access en **Authorize** y prueba cualquier endpoint desde el navegador.
- **ReDoc**: `/api/redoc/` — lectura cómoda.
- **OpenAPI 3 schema**: `/api/schema/` — o genera el archivo y valídalo:

```bash
poetry run python manage.py spectacular --file schema.yml --validate
```

## Permisos

| Quién | Leer recetas/ingredientes | Escribir recetas | Planes |
|-------|---------------------------|------------------|--------|
| Anónimo | ✅ | ❌ 401 | ❌ 401 |
| Usuario autenticado | ✅ | Solo **sus** recetas (403 en ajenas) | Solo **los suyos** (404 en ajenos) |
| Staff | ✅ | También recetas huérfanas (sin autor) | — |

## Tests y certificación

```bash
poetry run python manage.py test                          # 80 tests (suite formal)
poetry run python scripts/client_flow.py                  # 72 verificaciones HTTP de punta a punta
poetry run python scripts/client_flow.py https://tu-api   # el mismo flujo contra cualquier URL
```

El script de certificación **simula un cliente real**: registro → login → CRUD completo → permisos entre usuarios → refresh/logout, verificando **persistencia** (re-lee después de escribir). Deja usuarios de prueba con timestamp (limpiables desde el admin).

## Settings por entorno

```
config/settings/
├── base.py        # común a todos
├── local.py       # desarrollo (DEBUG + email a consola)
└── produccion.py  # producción (DEBUG=False, HTTPS/cookies/HSTS, STATIC_ROOT, SMTP)
```

- `manage.py` usa **local**; `wsgi.py` / `asgi.py` usan **produccion** (override con `DJANGO_SETTINGS_MODULE`).
- Verificación del perfil de producción:

```bash
poetry run python manage.py check --deploy --settings=config.settings.produccion
```

## Estructura del proyecto

```
apps/
├── user/       # User custom + autenticación (registro, JWT)
├── recipes/    # Recipe, Ingredient, RecipeIngredient + API
└── plan/       # Plan, PlanMeal + API
config/
├── settings/   # base / local / produccion
├── urls.py     # rutas raíz + schema/docs
└── wsgi|asgi
scripts/        # client_flow.py (certificación end-to-end)
tests/          # tests transversales (documentación OpenAPI)
```

## Roadmap

- [x] CRUD de recetas e ingredientes con líneas anidadas
- [x] Planificación semanal con comidas por día y tipo
- [x] Autenticación JWT (registro, login, refresh con rotación, logout con blacklist)
- [x] Permisos por dueño y aislamiento de planes por usuario
- [x] Paginación uniforme y estable
- [x] Documentación OpenAPI (Swagger UI + ReDoc) y suite de 80 tests
- [x] Settings por entorno + perfil de producción verificado
- [x] Script de certificación de cliente (72 verificaciones)
- [x] Throttling del login (anti fuerza bruta)
- [x] Email único en el registro
- [x] Endpoint `/health`
- [ ] CI con GitHub Actions
- [ ] Deploy (PaaS o VPS)
- [ ] Lista de compras + escalado de porciones
- [ ] Curación de ingredientes (evitar borrados que afecten recetas ajenas)

## Licencia

MIT.
