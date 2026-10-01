Temporal is opt-in: `docker compose --profile temporal up -d temporal` (UI on http://localhost:8233).
The API does not require it; workflows currently run through `app.workflows.runner.LocalRunner`.
