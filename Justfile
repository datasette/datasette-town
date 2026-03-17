# Type generation
types-routes:
  uv run python -c 'from datasette_town.router import router; import json; print(json.dumps(router.openapi_document_json()))' \
    | npx --prefix frontend openapi-typescript > frontend/api.d.ts

types-pagedata:
  uv run scripts/typegen-pagedata.py
  for f in frontend/src/page_data/*_schema.json; do \
    npx --prefix frontend json2ts "$f" > "${f%_schema.json}.types.ts"; \
  done

types:
  just types-routes
  just types-pagedata

# Frontend building
frontend *flags:
    npm run build --prefix frontend {{flags}}

frontend-dev *flags:
    npm run dev --prefix frontend -- --port 5180 {{flags}}

# Development servers
dev *flags:
    DATASETTE_SECRET=abc123 \
      uv run \
        --with datasette-debug-gotham \
        datasette \
        -p 8005 \
        -s permissions.datasette-town-access.newsroom "daily-planet" \
        {{flags}}

dev-with-hmr *flags:
    DATASETTE_TOWN_VITE_PATH=http://localhost:5180/ \
    watchexec \
      --stop-signal SIGKILL \
      -e py,html \
      --ignore '*.db' \
      --restart \
      --clear -- \
      just dev {{flags}}
