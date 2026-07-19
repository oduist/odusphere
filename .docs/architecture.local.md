# OduSphere — Sphere System Map (local)

> **Sphere-owned companion to `.docs/architecture.md`.** The upstream template
> never ships or edits this file, so it can never conflict on `git merge`.
> **This is where you document THIS sphere's own `odu_*` modules** — the same
> "signatures and relations only, no code, no logic bodies" rule as the core map.
>
> Read **both** `.docs/architecture.md` (upstream core) **and** this file at the
> start of every session to load the complete picture.
>
> Do **not** add sphere modules to `.docs/architecture.md` — that file is
> upstream-owned and would conflict on the next update.

## Modules
| Module | Purpose | Depends | SPEC |
|---|---|---|---|
| `odu_contacts` | Top-level **Contacts** workspace: `res.partner` directory + `odu.contact.message` requests with a triage workflow, chatter and activities. | `odu_base`, `mail` | `addons/odu_contacts/doc/tech_spec.md` |
| `odu_s3_attachment` | Offload user `ir.attachment` binaries to one or more S3-compatible object stores; serve via presigned URLs; keep Odoo's own web assets local. | `odu_base`, `web` | `addons/odu_s3_attachment/doc/tech_spec.md` |

## Contacts Models
- `odu.contact.message` (`odu_contacts`) — extends the `odu_base` model via
  `_inherit = ["odu.contact.message", "mail.thread", "mail.activity.mixin"]` (adds chatter +
  activities). New fields: `state` (Selection `new`/`in_progress`/`done`, default `new`, req,
  index, tracking), `user_id` (Many2one → `res.users`, "Assigned To", index, tracking).
  - `create(self, vals_list)` — `@api.model_create_multi` override; `super()` then `_odu_sync_handled()`.
  - `write(self, vals)` — override; `super()` then `_odu_sync_handled()` when `state` in `vals`.
  - `_odu_sync_handled(self)` — sets core `handled = (state == "done")`; one-directional, writes on change only.

## Client Actions & Menus
- `action_odu_contact_requests` (`ir.actions.act_window`, `odu.contact.message`, `kanban,list,form`, search default `open`) — the Requests inbox.
- `action_odu_contacts_partners` (`ir.actions.act_window`, `res.partner`, `kanban,list,form`, reuses framework views) — the Contacts directory.
- Menu `menu_odu_contacts_root` — "Contacts", top-level app (no `groups`), sequence 10.
  - `menu_odu_contacts_partners` — "Contacts", sequence 10 → `action_odu_contacts_partners`.
  - `menu_odu_contacts_requests` — "Requests", sequence 20 → `action_odu_contact_requests`.
- Views for `odu.contact.message`: `view_odu_contact_message_{list,kanban,form,search}` (form has statusbar `state` + `<chatter/>`).

## Security Surface
- `odu_contacts`: `base.group_user` (all internal users) full CRUD on `odu.contact.message`
  (additive to `odu_base`'s admin-only rule) and on `res.partner` (incl. `unlink`). Menus carry
  no `groups`.

## UI Overrides
- `odu_contacts` deactivates the core `odu_base.menu_odu_contact_messages` (Settings → Contact
  Requests) on install (`noupdate="1"` data record, `active=False`) — the Contacts → Requests
  workspace supersedes it.

## Cross-Module Relations
- `odu_contacts` → `depends(odu_base, mail)`. Extends `odu_base`'s `odu.contact.message`
  (adds `state`, `user_id`, `mail.thread`/`mail.activity.mixin`) and keeps the core `handled`
  flag in sync. `user_id` → `res.users`; Contacts directory reuses `res.partner` (framework views).
- Capture is unchanged: `odu_base`'s public `POST /api/contact` fills `odu.contact.message`
  (new records default to `state = new`).

## S3 Attachment Models
- `odu.s3.backend` (`odu_s3_attachment`) — `Model`; one S3-compatible store. `_order="sequence, id"`. Fields: `name` (Char req), `code` (Char req, `unique`, slug `^[a-z0-9][a-z0-9_-]*$`, embedded in markers — immutable while objects exist), `active` (Bool, default True), `sequence` (Int, default 10), `endpoint_url` (Char; empty=AWS), `public_endpoint_url` (Char; presign host), `bucket` (Char req; immutable while objects exist), `region` (Char), `access_key`/`secret_key` (Char req; admin-only), `mimetype_prefixes` (Char; comma-sep filter, empty=catch-all), `status` (Char compute, cheap/no-network).
  - `@api.model _s3_pick_backend(mimetype, size) -> record` — first active backend by sequence whose MIME filter matches; empty if none.
  - `_s3_matches(mimetype, size) -> bool`; `@api.model _s3_has_backend(include_archived=False) -> bool`.
  - `_s3_key(checksum)`, `_s3_marker(checksum) -> "s3://<code>/<sha[:2]>/<sha>"`, `@api.model _s3_backend_for_marker(fname) -> (record, key)` (resolves by code, `active_test=False`).
  - `_s3_settings(public)`, `_s3_client(public)`, `_s3_upload(checksum, data, mimetype) -> marker`, `_s3_read(key, size) -> bytes`, `_s3_delete(key)`, `_s3_presigned_url(key, download, filename, ttl) -> url|False`.
  - `_compute_status`, `_s3_probe() -> str`, `action_test_connection()` (button → notification).
  - `write(vals)` override — blocks changing `code`/`bucket` once `_s3_has_objects()`; `unlink()` blocks deletion while live or GC-queued markers exist (raise `UserError`); `_s3_has_objects() -> bool` checks `ir.attachment` + `odu.s3.gc`.
  - `@api.constrains("code")` — slug format; SQL `unique(code)`.
- `odu.s3.gc` (`odu_s3_attachment`) — `Model`, table `odu_s3_gc`; deferred-deletion spool. Field: `store_fname` (Char req, `index`, `unique`).
- `odu.s3.settings` (`odu_s3_attachment`) — `TransientModel`; global routing + migration console over `ir.config_parameter` (no `res.config.settings`). Fields: `keep_assets_local`, `keep_images_below_kb`, `keep_local_mimetypes`, `direct_download`, `signed_url_ttl`, `migrate_batch_size`, `migrate_window_start/end/tz`, RO diagnostics `backend_count`/`migrated_count`/`local_count`/`migration_running`. `default_get` loads, `action_apply`/`action_migrate_start`/`action_migrate_stop`/`action_refresh`.
- `ir.attachment` (`odu_s3_attachment`) — `_inherit`; no new fields. Storage/serving/migration/GC. Constants `_S3_PREFIX="s3://"`, `_S3_ASSET_MIMETYPES`.
  - Routing: `_s3_should_offload(mimetype, size)`, `_s3_direct_download_enabled()`, `_s3_signed_ttl()`, `_s3_is_s3(fname)`, `_odu_s3_pending()` (cursor-scoped checksum→(backend_id, mimetype) map).
  - Storage overrides: `_get_datas_related_values(data, mimetype)` (reroutes `store_fname`→marker + records pending), `@api.model _file_write(bin_value, checksum)` (uploads to pending backend), `@api.model _file_read(fname, size=None)`, `@api.model _file_delete(fname)`, `_s3_mark_for_gc(fname)` (separate cursor).
  - Serving: `_to_http_stream()` override → `_s3_http_stream()` (302 presigned URL or data stream), `_s3_transform_requested()`.
  - Migration: `_s3_offload()`, `_s3_offload_one()` (row/table-locked conditional storage-level SQL swap), `_s3_migrate_domain/_local_pending_count/_migrated_count/_is_running/_in_window/_set_flag/_set_running`, `@api.model _cron_odu_s3_migrate()` (per-record savepoints; failures remain active for retry).
  - GC: `@api.autovacuum _gc_odu_s3_store()`, `_gc_odu_s3_collect() -> int` (dedup-aware, rollback-cleanup, multi-backend including archived stores).

## Helpers (non-ORM)
- `odu_s3_attachment/models/s3_client.py` → `HAS_BOTO3`, `get_client(settings, public=False)` (process-cached boto3 client), `upload_dedup(client, bucket, key, data, content_type=None) -> bool`.

## HTTP Endpoints
- None new. Direct download rides the core `/web/content` + `/web/image` routes: `ir.attachment._to_http_stream` returns a `Stream(type="url")` → core emits a **302** to the presigned URL (access rights already enforced by `ir.binary._find_record`).

## Automation
- Cron `ir_cron_odu_s3_migrate` (`odu_s3_attachment`; `ir.attachment`, `state=code`, `model._cron_odu_s3_migrate()`, 30 min, `active=False` by default, `noupdate="1"`).
- `@api.autovacuum ir.attachment._gc_odu_s3_store` (daily `ir.autovacuum`).

## Client Actions & Menus
- `action_odu_s3_backend` (`ir.actions.act_window`, `odu.s3.backend`, `list,form`) ↔ menu `menu_odu_s3_backends` "Backends".
- `action_odu_s3_settings` (`ir.actions.act_window`, `odu.s3.settings`, `form`, `target=current`) ↔ menu `menu_odu_s3_settings` "Storage Settings".
- Menu root `menu_odu_s3_root` "S3 Storage" under `base.menu_administration` (Settings), sequence 90 — all `groups="base.group_system"`.

## Cross-Module Relations
- `odu_s3_attachment` → `depends(odu_base, web)` (governance base per ODUSPHERE §3; `web` for `ir.binary`/`Stream` serving).
- Extends core `ir.attachment` storage hooks (`_get_datas_related_values`, `_file_write/read/delete`) and the serving hook (`_to_http_stream`); no ORM relations to other `odu_*` modules. Backend credentials are read via `sudo()` by storage/serving code running as ordinary/public users.
