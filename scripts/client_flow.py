"""Flujo de cliente de punta a punta contra una API en vivo.

Simula una aplicacion cliente tipica: registro, login, uso autenticado,
errores de dominio, propiedad entre usuarios, refresh con rotacion y logout.
Verifica ESTADO (re-lee despues de escribir), no solo codigos HTTP:
un 201 no prueba que guardo; un 204 no prueba que borro.

Uso:
    poetry run python scripts/client_flow.py [base_url]

Requiere el servidor arriba (poetry run python manage.py runserver).
"""

import datetime
import json
import sys
import time
import urllib.error
import urllib.request

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"

PASSWORD = "flujo-cliente-2026"

ok_count = 0
fail_count = 0
failures = []


class FlowError(Exception):
    pass


def request(method, path, *, token=None, body=None, headers=None):
    """Realiza la peticion y devuelve (status, data) sin lanzar por HTTP >= 400."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for header_name, header_value in (headers or {}).items():
        req.add_header(header_name, header_value)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = None
        return exc.code, payload


def check(step, actual, expected):
    """Acumula una verificacion no critica."""
    global ok_count, fail_count
    options = expected if isinstance(expected, (list, tuple, set)) else (expected,)
    if actual in options:
        ok_count += 1
        print(f"  [ok]    {step} -> {actual}")
        return True
    fail_count += 1
    failures.append(step)
    print(f"  [FALLO] {step} -> {actual} (esperado {sorted(options)})")
    return False


def must(step, actual, expected):
    """Verificacion critica: si falla, aborta el flujo (los datos quedan para inspeccion)."""
    if not check(step, actual, expected):
        raise FlowError(f"Paso critico fallido: {step} (obtuvo {actual})")
    return actual


def banner(text):
    print(f"\n--- {text} ---")


def main():
    stamp = int(time.time())
    user_a, user_b = f"flow_a_{stamp}", f"flow_b_{stamp}"

    banner("Fase A: anonimo y autenticacion")
    status, _ = request("GET", "/api/recipes/")
    must("A1 lectura publica sin token", status, 200)

    status, body = request("POST", "/api/auth/register/", body={
        "username": user_a, "password": PASSWORD,
        "country": "Venezuela", "date_birth": "1990-01-01",
    })
    must("A2 registro usuario A", status, 201)
    user_a_id = body["id"]

    status, body = request("POST", "/api/auth/register/", body={
        "username": user_a, "password": PASSWORD,
        "country": "Venezuela", "date_birth": "1990-01-01",
    })
    check("A3 registro duplicado rechazado", status, 400)
    check("A3b error apunta a username", "username" in (body or {}), True)

    status, _ = request("POST", "/api/auth/register/", body={
        "username": f"flow_weak_{stamp}", "password": "123",
        "country": "Venezuela", "date_birth": "1990-01-01",
    })
    check("A4 password debil rechazada", status, 400)

    status, body = request("POST", "/api/auth/token/", body={"username": user_a, "password": PASSWORD})
    must("A5 login usuario A", status, 200)
    access_a, refresh_a = body["access"], body["refresh"]

    status, _ = request("POST", "/api/auth/token/", body={"username": user_a, "password": "wrong-password"})
    check("A6 credenciales malas rechazadas", status, 401)

    status, body = request("GET", "/api/plans/", token=access_a)
    must("A7 lista de planes autenticada", status, 200)
    check("A7b sobre de paginacion presente", "count" in (body or {}), True)

    status, _ = request("POST", "/api/plans/", body={})
    check("A8 anonimo no puede crear datos", status, 401)

    status, _ = request("GET", "/api/plans/", token="token-basura")
    check("A9 token invalido rechazado", status, 401)

    banner("Fase B: ingredientes (crear, leer, editar)")
    ing1 = f"Quinoa-flow-{stamp}"
    ing2 = f"Tomate-flow-{stamp}"
    status, body = request("POST", "/api/ingredients/", token=access_a, body={"name": ing1, "unit": "g"})
    must("B1 crear ingrediente", status, 201)
    ing1_id = body["id"]

    status, body = request("GET", f"/api/ingredients/{ing1_id}/")
    must("B2 re-leer el ingrediente", status, 200)
    check("B2b el nombre persistio", body["name"], ing1)

    status, _ = request("PATCH", f"/api/ingredients/{ing1_id}/", token=access_a, body={"unit": "kilogramos"})
    check("B3 actualizar ingrediente", status, 200)
    status, body = request("GET", f"/api/ingredients/{ing1_id}/")
    check("B4 la unidad nueva persiste", body["unit"], "kilogramos")

    status, body = request("POST", "/api/ingredients/", token=access_a, body={"name": ing2, "unit": "unidades"})
    must("B5 crear segundo ingrediente", status, 201)
    ing2_id = body["id"]

    banner("Fase C: receta con lineas (nido, persistencia, validaciones)")
    status, body = request("POST", "/api/recipes/", token=access_a, body={
        "name": f"Receta-flow-{stamp}", "instructions": "Paso uno. Paso dos.",
        "prep_time": 0.5, "servings": 4,
    })
    must("C1 crear receta", status, 201)
    recipe_id = body["id"]
    check("C1b el autor lo pone el servidor", body["created_by"], user_a_id)

    status, body = request("POST", f"/api/recipes/{recipe_id}/recipe-ingredients/", token=access_a, body={"ingredient_id": ing1_id, "quantity": 2})
    must("C2 agregar linea 1 (anidada)", status, 201)
    line1_id = body["id"]
    check("C2b la linea trae el ingrediente anidado", body["ingredient"]["name"], ing1)

    status, body = request("POST", f"/api/recipes/{recipe_id}/recipe-ingredients/", token=access_a, body={"ingredient_id": ing2_id, "quantity": 500})
    must("C3 agregar linea 2", status, 201)
    line2_id = body["id"]

    status, body = request("GET", f"/api/recipes/{recipe_id}/")
    must("C4 re-leer la receta", status, 200)
    lines = body["recipe_ingredients"]
    check("C4b las 2 lineas persistieron", len(lines), 2)
    names = {item["ingredient"]["name"] for item in lines}
    check("C4c los ingredientes correctos", names == {ing1, ing2}, True)

    status, _ = request("PATCH", f"/api/recipes/{recipe_id}/", token=access_a, body={"servings": 6})
    check("C5 actualizar la receta", status, 200)
    status, body = request("GET", f"/api/recipes/{recipe_id}/")
    check("C6 las porciones nuevas persisten", body["servings"], 6)

    status, _ = request("PATCH", f"/api/recipe-ingredients/{line1_id}/", token=access_a, body={"quantity": 3})
    check("C7 actualizar cantidad de linea", status, 200)
    status, body = request("GET", f"/api/recipes/{recipe_id}/")
    line1 = next(item for item in body["recipe_ingredients"] if item["id"] == line1_id)
    check("C8 la cantidad nueva persiste", line1["quantity"], 3)

    status, body = request("POST", f"/api/recipes/{recipe_id}/recipe-ingredients/", token=access_a, body={"ingredient_id": ing1_id, "quantity": 9})
    check("C9 linea duplicada rechazada", status, 400)
    check("C9b error apunta a ingredient_id", "ingredient_id" in (body or {}), True)

    status, _ = request("PATCH", f"/api/recipe-ingredients/{line2_id}/", token=access_a, body={"ingredient_id": ing1_id})
    check("C10 linea convertida en duplicado rechazada", status, 400)

    status, _ = request("DELETE", f"/api/recipe-ingredients/{line2_id}/", token=access_a)
    check("C11 eliminar linea", status, 204)
    status, body = request("GET", f"/api/recipes/{recipe_id}/")
    check("C12 el borrado persiste (queda 1 linea)", len(body["recipe_ingredients"]), 1)

    banner("Fase D: plan semanal y comidas")
    status, body = request("POST", "/api/plans/", token=access_a, body={})
    must("D1 crear plan con defaults", status, 201)
    plan_id = body["id"]
    start_date = datetime.datetime.fromisoformat(body["start_date"].replace("Z", "+00:00")).date()
    check("D1b fin del plan = inicio + 7 dias", body["end_date"], (start_date + datetime.timedelta(days=7)).isoformat())

    meal_date = body["end_date"]
    status, body = request("POST", f"/api/plans/{plan_id}/meals/", token=access_a, body={"recipe_id": recipe_id, "date": meal_date, "meal_type": "lunch"})
    must("D2 agregar comida al plan", status, 201)
    meal_id = body["id"]
    check("D2b la comida trae el resumen de la receta", body["recipe"]["name"], f"Receta-flow-{stamp}")

    status, _ = request("POST", f"/api/plans/{plan_id}/meals/", token=access_a, body={"recipe_id": recipe_id, "date": meal_date, "meal_type": "lunch"})
    check("D3 comida duplicada en el slot rechazada", status, 400)

    beyond = (datetime.date.fromisoformat(meal_date) + datetime.timedelta(days=1)).isoformat()
    status, body = request("POST", f"/api/plans/{plan_id}/meals/", token=access_a, body={"recipe_id": recipe_id, "date": beyond, "meal_type": "lunch"})
    check("D4 fecha fuera del rango rechazada", status, 400)
    check("D4b error apunta a date", "date" in (body or {}), True)

    status, body = request("POST", f"/api/plans/{plan_id}/meals/", token=access_a, body={"recipe_id": recipe_id, "date": meal_date, "meal_type": "brunch"})
    check("D5 tipo de comida invalido rechazado", status, 400)
    check("D5b error apunta a meal_type", "meal_type" in (body or {}), True)

    status, _ = request("PATCH", f"/api/plan-meals/{meal_id}/", token=access_a, body={"meal_type": "dinner"})
    check("D6 actualizar la comida", status, 200)
    status, body = request("GET", f"/api/plans/{plan_id}/", token=access_a)
    check("D7 el cambio persiste (comida anidada)", body["meals"][0]["meal_type"], "dinner")

    status, _ = request("DELETE", f"/api/recipes/{recipe_id}/", token=access_a)
    check("D8 receta EN USO no se puede borrar", status, 400)

    banner("Fase E: propiedad (segundo usuario)")
    status, _ = request("POST", "/api/auth/register/", body={
        "username": user_b, "password": PASSWORD,
        "country": "Venezuela", "date_birth": "1991-02-02",
    })
    must("E0 registrar usuario B", status, 201)
    status, body = request("POST", "/api/auth/token/", body={"username": user_b, "password": PASSWORD})
    must("E0b login usuario B", status, 200)
    access_b = body["access"]

    status, _ = request("GET", f"/api/recipes/{recipe_id}/", token=access_b)
    check("E1 B puede LEER la receta ajena", status, 200)
    status, _ = request("PATCH", f"/api/recipes/{recipe_id}/", token=access_b, body={"servings": 99})
    check("E2 B no puede editar la receta ajena", status, 403)
    status, _ = request("DELETE", f"/api/recipes/{recipe_id}/", token=access_b)
    check("E3 B no puede borrar la receta ajena", status, 403)
    status, _ = request("GET", f"/api/plans/{plan_id}/", token=access_b)
    check("E4 el plan ajeno es invisible (404)", status, 404)
    status, _ = request("POST", f"/api/recipes/{recipe_id}/recipe-ingredients/", token=access_b, body={"ingredient_id": ing2_id, "quantity": 1})
    check("E5 B no puede tocar las lineas ajenas", status, 403)

    banner("Fase F: interceptor de refresh (el corazon del cliente)")
    status, _ = request("GET", "/api/plans/", token="access-vencido-simulado")
    check("F1 access invalido da 401", status, 401)

    status, body = request("POST", "/api/auth/token/refresh/", body={"refresh": refresh_a})
    must("F2 refrescar el access", status, 200)
    new_access, new_refresh = body["access"], body["refresh"]

    status, _ = request("GET", "/api/plans/", token=new_access)
    check("F3 reintento con el access nuevo funciona", status, 200)

    status, _ = request("POST", "/api/auth/token/refresh/", body={"refresh": refresh_a})
    check("F4 el refresh viejo murio (rotacion)", status, 401)

    status, _ = request("GET", "/api/plans/", token=access_a)
    check("F5 el access viejo sigue vivo (stateless)", status, 200)

    status, _ = request("POST", "/api/auth/token/verify/", body={"token": new_access})
    check("F6 verify valida el token", status, 200)

    banner("Fase G: logout y limpieza verificada")
    status, _ = request("POST", "/api/auth/token/blacklist/", body={"refresh": new_refresh})
    check("G1 logout (blacklist del refresh)", status, 200)
    status, _ = request("POST", "/api/auth/token/refresh/", body={"refresh": new_refresh})
    check("G2 el refresh quedo muerto", status, 401)
    status, _ = request("GET", "/api/plans/", token=new_access)
    check("G3 el access sobrevive al logout (stateless)", status, 200)

    status, _ = request("DELETE", f"/api/plan-meals/{meal_id}/", token=new_access)
    check("G4 eliminar comida", status, 204)
    status, _ = request("DELETE", f"/api/plans/{plan_id}/", token=new_access)
    check("G5 eliminar plan", status, 204)
    status, _ = request("GET", f"/api/plans/{plan_id}/", token=new_access)
    check("G6 el plan borrado da 404", status, 404)

    status, _ = request("DELETE", f"/api/recipe-ingredients/{line1_id}/", token=new_access)
    check("G7 eliminar linea", status, 204)
    status, _ = request("DELETE", f"/api/recipes/{recipe_id}/", token=new_access)
    check("G8 eliminar receta (ya libre)", status, 204)
    status, _ = request("GET", f"/api/recipes/{recipe_id}/")
    check("G9 la receta borrada da 404", status, 404)
    status, _ = request("GET", f"/api/recipe-ingredients/{line1_id}/")
    check("G10 la linea murio en cascada (404)", status, 404)

    status, _ = request("DELETE", f"/api/ingredients/{ing1_id}/", token=new_access)
    check("G11 eliminar ingrediente 1", status, 204)
    status, _ = request("GET", f"/api/ingredients/{ing1_id}/")
    check("G12 el ingrediente borrado da 404", status, 404)
    status, _ = request("DELETE", f"/api/ingredients/{ing2_id}/", token=new_access)
    check("G13 eliminar ingrediente 2", status, 204)

    banner("Fase H: salud e idempotencia")
    status, body = request("GET", "/health")
    check("H1 /health responde ok", status, 200)
    check("H1b la base de datos esta arriba", (body or {}).get("database"), "up")

    idem_payload = {
        "name": f"Idem-flow-{stamp}",
        "instructions": "Prueba de idempotencia.",
        "prep_time": 0.2,
        "servings": 2,
    }
    idem_headers = {"Idempotency-Key": f"flow-{stamp}"}
    status, body = request("POST", "/api/recipes/", token=new_access, body=idem_payload, headers=idem_headers)
    must("H2 crear receta con Idempotency-Key", status, 201)
    idem_recipe_id = body["id"]
    status, body = request("POST", "/api/recipes/", token=new_access, body=idem_payload, headers=idem_headers)
    check("H3 el reintento devuelve la MISMA receta", (status, body.get("id")) == (201, idem_recipe_id), True)
    status, _ = request("DELETE", f"/api/recipes/{idem_recipe_id}/", token=new_access)
    check("H4 limpieza de la receta idempotente", status, 204)

    print("\n==============================================")
    total = ok_count + fail_count
    print(f"RESULTADO: {ok_count}/{total} verificaciones OK")
    if failures:
        print("Fallos:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"Usuarios de prueba creados: {user_a}, {user_b} (limpiables desde el admin)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FlowError as exc:
        print(f"\nFLUJO ABORTADO: {exc}")
        print("Los datos creados hasta aqui quedan en la BD para inspeccion.")
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"\nNo se pudo conectar a {BASE_URL}: {exc.reason}")
        print("Levanta el servidor primero: poetry run python manage.py runserver")
        sys.exit(2)
