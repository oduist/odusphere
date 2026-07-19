# odu_s3_attachment — Module SPEC

## Identity & Manifest
- Technical name: `odu_s3_attachment`
- Display name: `S3 Attachment Storage`
- Summary: Offload user `ir.attachment` binaries to one or more S3-compatible object stores and serve them via presigned URLs.
- Version: `19.0.1.0.0` (Odoo 19)
- Category: `Technical` · Author: `OduSphere` · License: `LGPL-3`
- Flags: `application = False`, `installable = True`, `auto_install` not set.
- `depends`: `["odu_base", "web"]` — `odu_base` per OduSphere governance (§3); `web` for the HTTP binary-serving path (`ir.binary` / `Stream`, `/web/content`, `/web/image`).
- External Python libs: `boto3` (declared in `external_dependencies.python`). `botocore` ships with boto3. `pytz` (already an Odoo dependency) is used for the migration time window.
- `data`: `security/ir.model.access.csv`, `data/ir_cron.xml`, `views/odu_s3_backend_views.xml`, `views/odu_s3_settings_views.xml`, `views/odu_s3_menus.xml`.
- Assets: none.

## Models & Fields

### `odu.s3.backend` — `models.Model`
- `_description = "S3 Storage Backend"`, `_order = "sequence, id"`.
- One record = one S3-compatible object store. Several may be active at once; routing picks one per upload.
- Fields:
  - `name` (Char, `required=True`) — human label.
  - `code` (Char, `required=True`) — stable slug embedded verbatim in every stored object's `store_fname` marker (`s3://<code>/…`). Must match `^[a-z0-9][a-z0-9_-]*$`. **Immutable while objects exist**. `unique(code)` SQL constraint.
  - `active` (Boolean, `default=True`) — archived backends receive no new uploads but stay readable (marker still resolves; lookups use `active_test=False`).
  - `sequence` (Integer, `default=10`) — routing priority (lower first).
  - `endpoint_url` (Char) — S3 API endpoint; empty ⇒ AWS S3. Non-empty ⇒ path-style addressing (MinIO/R2/Ceph/…).
  - `public_endpoint_url` (Char) — host used to **sign** presigned URLs when the browser-facing address differs from the internal one; empty ⇒ sign against `endpoint_url`.
  - `bucket` (Char, `required=True`) — physical object location; **immutable while objects exist**.
  - `region` (Char).
  - `access_key` (Char, `required=True`).
  - `secret_key` (Char, `required=True`) — stored in DB; readable by administrators only (ACL). Shown with the `password` widget.
  - `mimetype_prefixes` (Char) — optional comma-separated MIME-type prefixes this backend claims; empty ⇒ catch-all.
  - `status` (Char, `compute="_compute_status"`, not stored) — **cheap** completeness string (no network); the live check is the Test Connection button.

### `odu.s3.gc` — `models.Model`
- `_description = "S3 Attachment GC Queue"`. Table `odu_s3_gc`.
- Deferred-deletion spool for S3 objects (DB analogue of the core filestore "checklist").
- Fields: `store_fname` (Char, `required=True`, `index=True`) — the `s3://<code>/<key>` marker queued for deletion. SQL `unique(store_fname)` (enables `INSERT … ON CONFLICT DO NOTHING`).

### `odu.s3.settings` — `models.TransientModel`
- `_description = "S3 Storage Settings"`. Global routing + migration console. **Not** `res.config.settings` (avoids a `base_setup` dependency, which is outside the OduSphere allowed framework set). Every value is an `ir.config_parameter`, loaded in `default_get`, written in `action_apply`.
- Fields (persisted params in parentheses):
  - `keep_assets_local` (Boolean, default `True`) → `odu_s3_attachment.keep_assets_local`.
  - `keep_images_below_kb` (Integer, default `50`) → `odu_s3_attachment.keep_images_below_kb`.
  - `keep_local_mimetypes` (Char) → `odu_s3_attachment.keep_local_mimetypes`.
  - `direct_download` (Boolean, default `True`) → `odu_s3_attachment.direct_download`.
  - `signed_url_ttl` (Integer, default `30`) → `odu_s3_attachment.signed_url_ttl`.
  - `migrate_batch_size` (Integer, default `100`) → `odu_s3_attachment.migrate_batch_size`.
  - `migrate_window_start` / `migrate_window_end` (Integer, default `0`) → `odu_s3_attachment.migrate_window_start` / `_end`.
  - `migrate_window_tz` (Char) → `odu_s3_attachment.migrate_window_tz`.
  - Read-only diagnostics (computed in `default_get`, not stored params): `backend_count`, `migrated_count`, `local_count`, `migration_running`.

### `ir.attachment` — `_inherit = "ir.attachment"`
- No new stored fields. Adds routing/storage/serving/migration/GC behavior. Class constants:
  - `_S3_PREFIX = "s3://"` (imported from `odu_s3_backend.S3_PREFIX`).
  - `_S3_ASSET_MIMETYPES = ("text/css", "application/javascript", "text/javascript")`.

### `ir.config_parameter` keys owned by this module
`odu_s3_attachment.keep_assets_local` (default `True`), `.keep_images_below_kb` (`50`), `.keep_local_mimetypes` (`""`), `.direct_download` (`True`), `.signed_url_ttl` (`30`), `.migrate_batch_size` (`100`), `.migrate_window_start`/`.migrate_window_end` (`0`), `.migrate_window_tz` (`""`), `.migrate_active` (`"0"`/`"1"` — internal migration flag, read by raw SQL to bypass the ORM cache).

## Constraints & Invariants
- `odu.s3.backend`: SQL `unique(code)`. `@api.constrains("code")` — code must match `^[a-z0-9][a-z0-9_-]*$`, else `ValidationError`. `_s3_has_objects()` covers markers referenced by attachments or awaiting remote deletion in `odu.s3.gc`. `write` refuses to change `code` or `bucket` while either exists, and `unlink` refuses to delete such a backend, raising `UserError` — protects both reads and pending cleanup. Endpoint and credential rotation remain allowed.
- `odu.s3.gc`: SQL `unique(store_fname)`.
- **Marker↔location invariant:** an attachment's `store_fname` starting with `s3://<code>/` means its bytes live on the backend with that `code`, at object key `<sha[:2]>/<sha>`. Reads/deletes/serving resolve the backend from the marker; the local filestore is used for every non-`s3://` `store_fname` (automatic fallback for not-yet-migrated files).
- **Dedup invariant:** object key = SHA1 of content (content-addressed, same as native filestore) ⇒ identical content shares one object. Within a single transaction, identical content (same checksum) is routed to a **single** backend even if declared MIME types differ (coalesced via the pending map), so the deduplicated write and every marker agree.
- **GC dedup-safety:** a queued object is deleted only when **no** `ir.attachment.store_fname` still references its marker.

## Business Rules & State

### Routing decision (local vs S3, and which S3)
1. **Keep-local filter** `_s3_should_offload(mimetype, size)` → eligible for S3 unless: `keep_assets_local` and mimetype ∈ asset mimetypes; or `keep_images_below_kb > 0` and `image/*` with `size ≤ kb*1024`; or mimetype starts with any prefix in `keep_local_mimetypes`. Empty mimetype ⇒ eligible.
2. **Backend selection** `odu.s3.backend._s3_pick_backend(mimetype, size)` → first **active** backend, in `sequence` order, whose `_s3_matches` accepts the mimetype (empty `mimetype_prefixes` = catch-all). No match ⇒ empty ⇒ content stays local.
3. Only content core placed in the filestore (`store_fname` set; not `db` storage) is rerouted.

### Write path (Odoo 19 storage refactor)
- `_get_datas_related_values(data, mimetype)` (has mimetype+size) decides routing, overwrites `values["store_fname"]` with the backend marker, sets `db_datas = False`, and records `pending[checksum] = (backend_id, mimetype)`.
- The actual upload happens in the later, separate `_file_write(bin_value, checksum)` call (whose return value core ignores). The two are bridged by a **transaction-scoped map** on the cursor (`cr._odu_s3_pending_map`, keyed by checksum), because in v19 `_file_write` only receives the checksum, not the mimetype. `_file_write` pops the entry and uploads to that backend; absent entry ⇒ local `super()._file_write`.
- Before every S3 upload, `_s3_upload` writes the prospective marker to the separately committed GC spool. If the surrounding PostgreSQL transaction commits, GC sees the live marker and drops the spool row; if it rolls back, GC removes the unreferenced remote object. Attachment create/write already holds a row-exclusive table lock, so GC cannot race the uncommitted database reference.

### Serving path
- `_to_http_stream()` (called by `ir.binary._record_to_stream` for `/web/content`, `/web/image`, mail, reports, …) is overridden: S3-backed attachments build their own `Stream`; local ones delegate to `super()`. Access control is already enforced by `ir.binary._find_record` before this runs.
- `_s3_http_stream()`: if `direct_download` is on **and** no image transform is requested → `Stream(type="url", url=<presigned>, max_age=0)` ⇒ core issues a **302** redirect (no-cache). Otherwise → `Stream(type="data")` with bytes read back from S3 (streamed through Odoo). Presigned download disposition is requested when `request.params["download"]` is set.
- `_s3_transform_requested()`: true when `request.params` has a truthy `width`/`height`/`quality`, `crop`, or an Image field name whose dimensions are derived by Odoo (for example `avatar_128`). Transforms must not redirect because core needs the bytes to resize/crop.

### Migration (existing local → S3)
- Storage-level relocation that **bypasses the ORM `write` chain** (no sibling write hooks): acquire a row-exclusive table lock (excludes GC) and `FOR UPDATE` row lock (serializes replacement/deletion) → read local bytes → upload to routed backend → conditionally `UPDATE ir_attachment SET store_fname` only while the original location still matches → `invalidate_recordset` → `_file_delete(old_local)` (local GC). Skips non-binary, already-S3, keep-local, and unreadable-source (read length ≠ `file_size`) records; skips when no backend matches.
- Gated by flag + time window; each attachment runs in a savepoint and batches commit independently. A failed attachment leaves migration active for a later cron retry; the flag clears only after an error-free full sweep.

### Garbage collection
- `_file_delete(fname)` on an S3 marker enqueues it in `odu_s3_gc` via a **separate cursor** (survives rollback); local fnames go to `super()`.
- `@api.autovacuum _gc_odu_s3_store` runs when any active **or archived** backend exists, locks `ir_attachment SHARE`, then `_gc_odu_s3_collect` deletes each queued object whose marker is unreferenced by any attachment, resolving the backend per marker (multi-backend). Unresolvable markers are kept in the queue (logged), not dropped.

## Methods & Actions

### `odu.s3.backend`
- `_compute_status(self)` — cheap status string (no network). Trigger: form display.
- `_s3_probe(self) -> str` — live `head_bucket` reachability check; returns status text. Trigger: `action_test_connection`.
- `action_test_connection(self)` — button; returns a `display_notification` client action with `_s3_probe()`.
- `write(self, vals)` — override; blocks changing `code` or `bucket` when `_s3_has_objects()` (raises `UserError`); endpoint and credential changes remain allowed.
- `unlink(self)` — override; blocks deleting a backend when `_s3_has_objects()` (raises `UserError`), directing administrators to archive it.
- `_s3_has_objects(self) -> bool` — true if any attachment `store_fname` marker or `odu.s3.gc` pending-deletion marker points at this backend (`=like s3://<code>/%`; attachment query uses the res_field OR-trick).
- `@api.model _s3_pick_backend(self, mimetype, size) -> record` — routing (see rules); returns empty if none.
- `_s3_matches(self, mimetype, size) -> bool` — MIME-filter predicate (empty filter = catch-all).
- `@api.model _s3_has_backend(self, include_archived=False) -> bool` — active-only existence gate by default; `include_archived=True` disables `active_test` for GC.
- `_s3_key(self, checksum) -> "<sha[:2]>/<sha>"`; `_s3_marker(self, checksum) -> "s3://<code>/<key>"`.
- `@api.model _s3_backend_for_marker(self, fname) -> (record, key)` — parse `s3://<code>/<key>`; resolves backend by code with `active_test=False`; `(empty, "")` if unresolved.
- `_s3_settings(self, public=False) -> dict`; `_s3_client(self, public=False)` — cached boto3 client (via `s3_client.get_client`).
- `_s3_upload(self, checksum, data, mimetype=None) -> marker` — commits a rollback-cleanup GC intent, performs dedup-aware `put_object`, returns marker.
- `_s3_read(self, key, size=None) -> bytes` — `get_object` (honours `size`); `b""` on error.
- `_s3_delete(self, key)` — `delete_object`.
- `_s3_presigned_url(self, key, download=False, filename=None, ttl=30) -> url|False` — `generate_presigned_url("get_object", …)`, signed via the public client; `ResponseContentDisposition=attachment` when `download`.

### `ir.attachment`
- `_s3_should_offload(self, mimetype, size) -> bool` — keep-local filter (see rules).
- `_s3_direct_download_enabled(self) -> bool`; `_s3_signed_ttl(self) -> int` — read the params.
- `_s3_is_s3(self, fname) -> bool` — marker predicate.
- `_odu_s3_pending(self) -> dict` — get/create the cursor-scoped checksum→(backend_id, mimetype) map.
- `_get_datas_related_values(self, data, mimetype) -> values` — override; reroutes `store_fname` to a backend marker + records pending (see write path).
- `@api.model _file_write(self, bin_value, checksum) -> fname` — override; uploads to the pending backend or `super()` (local).
- `@api.model _file_read(self, fname, size=None) -> bytes` — override; reads from the marker's backend or `super()`; `b""` if the marker's backend is unknown.
- `@api.model _file_delete(self, fname)` — override; enqueues S3 markers for GC (`_s3_mark_for_gc`) or `super()`.
- `_s3_mark_for_gc(self, fname)` — separate-cursor `INSERT … ON CONFLICT DO NOTHING` into `odu_s3_gc`.
- `_to_http_stream(self) -> Stream` — override; S3 attachments via `_s3_http_stream`, else `super()`.
- `_s3_http_stream(self) -> Stream` — presigned-URL 302 or data stream (see serving path).
- `_s3_transform_requested(self) -> bool` — detects `/web/image` resize/crop.
- `_s3_offload(self) -> int`; `_s3_offload_one(self) -> bool` — storage-level relocation (see migration).
- `@api.model _s3_migrate_domain(self) -> domain`; `_s3_local_pending_count`; `_s3_migrated_count` — migration accounting (domains include the `res_field` OR-trick to cover binary-field attachments).
- `@api.model _s3_migrate_is_running(self) -> bool` — raw SQL read of `migrate_active` (bypasses ORM cache).
- `@api.model _s3_migrate_in_window(self) -> bool` — time-window check (tz-aware; `start==end` disables; supports overnight).
- `@api.model _s3_migrate_set_flag(self, value)` — set `migrate_active` + `flush_model(["value"])`.
- `@api.model _s3_migrate_set_running(self, running)` — admin-only; validates a backend exists when starting; flips flag; best-effort (de)activates + `_trigger()`s the cron.
- `@api.model _cron_odu_s3_migrate(self)` — background worker (flag + window gated, id-ordered batches, per-batch commit, clears flag when done). Trigger: cron `ir_cron_odu_s3_migrate` (every 30 min, inactive by default).
- `@api.autovacuum _gc_odu_s3_store(self)`; `_gc_odu_s3_collect(self) -> int` — dedup-aware, multi-backend orphan sweep.

### `odu.s3.settings`
- `@api.model default_get(self, fields_list)` — load params + diagnostics.
- `action_apply(self)` — persist all params, return a reload action.
- `action_migrate_start(self)` / `action_migrate_stop(self)` — persist, then `ir.attachment._s3_migrate_set_running(True/False)`; reload.
- `action_refresh(self)` — reload (recompute counters).
- `_reload(self) -> act_window` — reopen the settings form (`target=current`).

### `s3_client.py` (module-level helpers, non-ORM)
- `HAS_BOTO3` (bool). `get_client(settings, public=False)` — process-cached boto3 client keyed by `(endpoint, access_key, secret_key, region)`; `public` selects `public_endpoint_url`; path-style addressing + `s3v4` + `max_pool_connections=64`. `upload_dedup(client, bucket, key, data, content_type=None) -> bool` — `head_object` then `put_object`, returns whether it uploaded.

## Security
- `security/ir.model.access.csv` — full CRUD to `base.group_system` **only** for `odu.s3.backend`, `odu.s3.gc`, `odu.s3.settings`. No other group has access.
- No new groups, no record rules.
- Credentials (`access_key`/`secret_key`) live in the DB, admin-readable only. Internal storage/serving code that runs as ordinary (or public) users reaches backends via `sudo()`; end users never touch the `odu.s3.backend` ACL directly.
- Serving enforces normal attachment access rights in `ir.binary._find_record` **before** a presigned URL is generated; the URL is short-lived (`signed_url_ttl`).
- `_s3_migrate_set_running` raises `AccessError` for non-administrators.

## Views & UI
- `odu.s3.backend`: list (`view_odu_s3_backend_list`, handle-sorted by `sequence`, `active` toggle), form (`view_odu_s3_backend_form`, Test Connection header button, archived ribbon, grouped Identity/Routing/Connection, `secret_key` password widget, readonly `status`), search (`view_odu_s3_backend_search`, Archived filter). Action `action_odu_s3_backend` (`list,form`).
- `odu.s3.settings`: form (`view_odu_s3_settings_form`) — Save/Refresh header buttons; sections "What stays in Odoo", "Direct download" (TTL hidden when `direct_download` is off), "Migrate existing attachments to S3" (counters + batch size + window + Start/Stop buttons toggled on `migration_running`). Action `action_odu_s3_settings` (`form`, `target=current`).
- Menus (`views/odu_s3_menus.xml`, all `groups="base.group_system"`): root `menu_odu_s3_root` "S3 Storage" under `base.menu_administration` (Settings) → `menu_odu_s3_backends` "Backends" (→ `action_odu_s3_backend`), `menu_odu_s3_settings` "Storage Settings" (→ `action_odu_s3_settings`).

## API Endpoints
- No new `http.route` controllers. Direct download reuses the core `/web/content` and `/web/image` routes: the override of `ir.attachment._to_http_stream` returns a `Stream(type="url")` → core emits a **302** to the presigned URL. Non-direct (or image-transform) requests stream S3 bytes through the same routes.

## Automation
- Cron `ir_cron_odu_s3_migrate` (`data/ir_cron.xml`, `noupdate="1"`): model `ir.attachment`, `state=code`, `code = model._cron_odu_s3_migrate()`, every 30 minutes, `active=False` by default (toggled by the migration Start/Stop console).
- `@api.autovacuum _gc_odu_s3_store` runs with the daily `ir.autovacuum` job.

## Seed / Demo Data
- None. No S3 backends are shipped; the module is inert until an administrator adds one.
