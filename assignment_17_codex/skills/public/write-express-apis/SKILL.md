---
name: write-express-apis
description: Write and modify simple Node.js Express APIs in JavaScript using JSON:API conventions, including server setup, routes, controllers, middleware, validation, and error handling. Use when asked to build or update backend APIs, add endpoints, implement CRUD resources, or create minimal Express services that must follow JSON:API.
---

# Write Express Apis

## Overview

Create or update simple Express APIs that follow JSON:API conventions with minimal dependencies and clear, maintainable structure.

## Workflow

1. Inspect the project structure and module system (CommonJS vs ESM). Match the existing style and file layout.
2. Confirm the API scope: resources, endpoints, data store (in-memory vs database), validation, auth, and JSON:API response shape. If unspecified, assume JSON:API CRUD with no auth and a simple in-memory or placeholder data layer.
3. Implement the routes and handlers using the smallest structure that fits: single `app.js` for tiny services, or a `routes/` + `controllers/` split for multi-resource APIs.
4. Add input validation, consistent status codes, and centralized error handling. Avoid extra libraries unless requested or already present.
5. Provide basic usage examples (`curl`) and describe any new environment variables or scripts.

## Default Conventions

- Base path: `/api`.
- JSON:API request/response with top-level `data`, `errors`, and optional `meta`.
- Status codes: `200`, `201`, `204`, `400`, `404`, `409`, `500`.
- Error shape: `{ "errors": [{ "status": "...", "title": "...", "detail": "...", "source": { "pointer": "..." } }] }`.
- Use `express.json()` and explicit `async` handlers with `next(err)`.

## References

- Read `references/express-rest-guidelines.md` for JSON:API route templates, validation patterns, and error-handling examples.
