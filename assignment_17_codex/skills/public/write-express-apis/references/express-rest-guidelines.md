# Express JSON:API Guidelines

## Project Structure Options

Use the smallest structure that fits the task and the existing repo.

- Single-file (tiny services):
  - `app.js` sets up middleware, routes, and error handler.
- Split by resource (typical CRUD):
  - `app.js` loads routers
  - `routes/<resource>.js` defines endpoints
  - `controllers/<resource>.js` implements handlers
  - `services/<resource>.js` optional if logic grows

## Route Patterns

Resource type: `items`

- `GET /api/items` list
- `GET /api/items/:id` fetch one
- `POST /api/items` create
- `PUT /api/items/:id` replace
- `PATCH /api/items/:id` partial update
- `DELETE /api/items/:id` delete

## Handler Skeleton (CommonJS)

```js
const express = require('express');
const router = express.Router();

router.get('/', async (req, res, next) => {
  try {
    res.json({ data: [] });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
```

## Validation (No Extra Libraries)

Keep it explicit and minimal unless a validation library is already present.

- Check required fields and types at the top of the handler.
- Return `400` with a clear message and field details.

Example:

```js
if (typeof name !== 'string' || !name.trim()) {
  return res.status(400).json({
    errors: [{
      status: '400',
      title: 'Invalid Attribute',
      detail: 'name is required',
      source: { pointer: '/data/attributes/name' }
    }]
  });
}
```

## Error Handling

Centralize error handling in `app.js`:

```js
app.use((err, req, res, next) => {
  const status = err.status || 500;
  const message = err.expose ? err.message : 'Internal Server Error';
  res.status(status).json({
    errors: [{
      status: String(status),
      title: status === 500 ? 'Server Error' : 'Request Error',
      detail: message
    }]
  });
});
```

## Data Layer Defaults

If no database is specified:

- Use an in-memory array or Map for examples.
- Keep IDs simple (incrementing number or UUID if already used).
- Clearly label in-memory usage as non-persistent.

## JSON:API Response Shape

Prefer consistent JSON:API shapes:

- Success list: `{ data: [ { type, id, attributes, relationships? } ] }`
- Success single: `{ data: { type, id, attributes, relationships? } }`
- Errors: `{ errors: [ { status, title, detail, source? } ] }`
- Optional: `{ meta: {...} }`, `{ links: {...} }`, `included: [...]`

## Request Shape

Create and update payloads:

```json
{
  "data": {
    "type": "items",
    "attributes": {
      "name": "Example"
    }
  }
}
```

## Common Status Codes

- `200` OK
- `201` Created (include `Location` when helpful)
- `204` No Content (delete)
- `400` Invalid input
- `404` Not found
- `409` Conflict (duplicate)
- `500` Server error

## JSON:API Conventions

- Use `type` and `id` fields for resources.
- `id` must be a string in responses.
- Validate `data.type` matches the resource in the URL.
- For `PATCH`, support partial updates of `attributes`.

## Minimal Security Defaults

- Use `express.json()`.
- If CORS needed, add only when requested or already present.
- Never log secrets.
