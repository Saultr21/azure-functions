# NormalizarPrecio

Función HTTP de Azure Functions que recibe un precio en **cualquier formato** (con símbolos de moneda, texto, espacios, etc.) y devuelve únicamente el valor numérico limpio.

## Descripción

Utiliza una expresión regular que elimina todo carácter que no sea un dígito o una coma, sin ningún valor hardcodeado. Funciona con cualquier moneda, idioma o formato sin configuración adicional.

### Ejemplos de entrada y salida

| Entrada (`precio`)  | Salida     |
|---------------------|------------|
| `euro 100, 00`      | `100,00`   |
| `€100,00`           | `100,00`   |
| `100,00 euro`       | `100,00`   |
| `USD 250`           | `250`      |
| `$ 1500,99`         | `1500,99`  |

## Endpoint

```
GET/POST /api/normalizar_precio
```

> Requiere autenticación de nivel **Function** (clave de función en el encabezado o query param `code`).

## Parámetros

El precio puede enviarse de dos formas:

### 1. Query string (GET o POST)

```
GET /api/normalizar_precio?precio=euro%20100,%2000
```

### 2. Body JSON (POST)

```json
{
  "precio": "euro 100, 00"
}
```

## Respuestas

###  200 OK  Precio normalizado correctamente

```
100,00
```

La respuesta es texto plano con el precio normalizado.

###  400 Bad Request  Campo `precio` ausente

```
Pasa el parámetro 'precio' en la query string o en el cuerpo JSON. Ejemplo: ?precio=euro%20100,%2000
```

## Lógica de limpieza

```python
re.sub(r'[^0-9,]', '', precio)
```

Elimina todo lo que no sea dígito (`0-9`) o coma (`,`). No hay listas de símbolos ni palabras hardcodeadas  cualquier carácter extra se descarta automáticamente.

## Dependencias

| Paquete           | Uso                          |
|-------------------|------------------------------|
| `azure-functions` | Framework de Azure Functions |
| `re`              | Expresiones regulares (stdlib) |
