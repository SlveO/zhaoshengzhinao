# Admin Analytics & Event Logging

## Event logging

Fire-and-forget pattern via `backend/core/event_writer.py`. All analytics data flows through `event_logs` table — modules read from it via raw SQL aggregation, never call each other directly. Always wrap in try/except to avoid blocking the main flow.

## Admin analytics modules

Each analytics endpoint (`/api/v1/admin/analytics/*`) is a separate module with its own SQL aggregation query file in `backend/analytics/`. Modules are gated by `tenant.config.modules` with dependency chains (e.g. `annual_report` requires `funnel` + `profile_dashboard` + `major_heatmap` + `region_distribution` + `competitive_analysis`).
