# EchoWell API reference

The API contract is the OpenAPI 3.1 document in [`api_reference/openapi.json`](api_reference/openapi.json). It is generated from the backend code and must never be edited by hand (TRD 25 AGT-061, TRD 24 D-51, D-89).

## Regenerating it

After any change to a router or DTO:

```bash
python -m backend.cli export-openapi > docs/api_reference/openapi.json
```

The command needs valid settings (a dummy `DATABASE_URL` is enough) but never connects to the database. Commit the regenerated file with the change. `tests/contract/test_openapi_contract.py` fails when the committed file and the code disagree.

## Where it comes from

| Part | Source |
|---|---|
| Paths, parameters, request and response schemas | FastAPI routers in `backend/api/` and DTOs in `backend/schemas/` |
| TRD 19 conventions (paths relative to `/api/v1`, per-operation security, shared error responses, `X-Request-ID`, named schemas such as `ResidentCode` and `PageMeta`) | `backend/api/openapi.py` |
| The design reference the document must match | TRD 19 §4.5 skeleton, stored as `tests/fixtures/trd19_openapi_skeleton.yaml`; endpoint notes in `docs/design/OpenAPI_Spec.md` |

## Viewing it

- Running API: `GET /api/v1/openapi.json` (every environment, no login).
- Swagger UI: `/api/v1/docs` in local, staging and test only; it is not served in production.

## Checks on every PR

- `tests/contract/test_openapi_contract.py`: the generated document equals the committed file, is valid OpenAPI 3.1, and matches the TRD 19 skeleton in paths, methods, security, status codes, parameters, request bodies and schemas. It also checks that no property carries audio, names or dates of birth.
- `tests/contract/response_validation.py`: every response in the integration API tests is validated against this document, including error bodies, and `meta` must appear exactly where the schema declares it.
- `tests/integration/db/test_enums.py`: the document's enums equal the database enums.
