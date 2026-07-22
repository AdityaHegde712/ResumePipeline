# Payload Generation Rules

How to construct request bodies and query parameters for each discovered endpoint.
The test runner (`scripts/run_tests.py`) imports these rules via Python logic, but
this document is the canonical source of truth for what that logic implements.

---

## Priority Order

For any field or parameter, resolve its value using this priority:

1. **Type hint + Pydantic model** — inspect the request body model's fields
2. **OpenAPI schema** — if a spec was the discovery source, use its `example` or
   `default` values first, then schema types
3. **Conservative default** — when no type information is available (see table below)
4. **Skip** — for file uploads, binary data, or WebSocket upgrades

---

## Type → Default Value Mapping

| Python / JSON type | Generated value | Notes |
|---|---|---|
| `str` | `"test"` | Generic non-empty string |
| `int` | `1` | Safe positive integer |
| `float` | `1.0` | |
| `bool` | `true` | |
| `list` / `List[T]` | `[<one item of type T>]` | Recurse for `T` |
| `dict` / `Dict[str, Any]` | `{}` | Empty object — safe conservative |
| `Optional[T]` / `T \| None` | `null` | Prefer null over guessing |
| `Enum` | first declared value | Import enum class and call `.value` |
| `datetime` | `"2024-01-01T00:00:00Z"` | ISO 8601 UTC |
| `date` | `"2024-01-01"` | ISO 8601 date |
| `UUID` | `"00000000-0000-0000-0000-000000000001"` | Deterministic test UUID |
| `EmailStr` | `"test@example.com"` | |
| `HttpUrl` | `"https://example.com"` | |
| `bytes` / `UploadFile` | — | **Skip endpoint; mark manual** |
| unknown / `Any` | `null` | Safest conservative value |

---

## Path Parameters

For dynamic segments like `/users/{user_id}` or `/items/{item_id:int}`:

- If the type is annotated as `int` or `UUID` — substitute the canonical test value
  from the table above
- If unannotated — substitute `"1"` (string, works for most backends)
- Log the substitution in `test_results.json` under `path_substitutions`

---

## Query Parameters

Treat query params identically to body fields — apply the same type → default
mapping. Only include required params; omit optional ones unless they have defaults
in the route definition.

---

## Request Headers

Always send:
```
Content-Type: application/json
Accept: application/json
```

If the env snapshot contains any of these keys, inject them automatically:

| Env key pattern (case-insensitive) | Header injected |
|---|---|
| `*API_KEY*`, `*APIKEY*` | `X-API-Key: <value>` |
| `*JWT*`, `*TOKEN*`, `*ACCESS_TOKEN*` | `Authorization: Bearer <value>` |
| `*BASIC_AUTH*` | `Authorization: Basic <value>` |
| `*SECRET*` (standalone) | Ignored — too ambiguous |

If multiple token-like keys exist, prefer the most specific match. Log which header
was injected in `test_results.json` under `headers_injected`.

---

## Nested Models

For a Pydantic model like:

```python
class Address(BaseModel):
    street: str
    city: str
    zip_code: str

class User(BaseModel):
    name: str
    age: int
    address: Address
```

Generate:
```json
{
  "name": "test",
  "age": 1,
  "address": {
    "street": "test",
    "city": "test",
    "zip_code": "test"
  }
}
```

Recurse to any depth. Circular references: stop recursing and substitute `{}`.

---

## Enums

```python
class Status(str, Enum):
    active = "active"
    inactive = "inactive"
```

Generated value: `"active"` (the first declared member).

---

## What NOT to generate

- Do not fabricate realistic-looking names, addresses, or PII data
- Do not generate random values — tests must be deterministic and reproducible
- Do not send `null` for required fields without a type hint if the field name
  strongly implies a type (e.g. `user_id` → use `1`, `email` → use `"test@example.com"`)

---

## Conservative-Default Heuristics (name-based fallbacks)

When type information is fully absent, use field name as a signal:

| Field name pattern | Fallback value |
|---|---|
| `*_id`, `id` | `1` |
| `*email*` | `"test@example.com"` |
| `*url*`, `*link*` | `"https://example.com"` |
| `*name*`, `*title*`, `*label*` | `"test"` |
| `*count*`, `*num*`, `*total*`, `*amount*` | `1` |
| `*date*`, `*at` (e.g. `created_at`) | `"2024-01-01T00:00:00Z"` |
| `*flag*`, `*enabled*`, `*active*`, `*is_*` | `true` |
| anything else | `null` |
