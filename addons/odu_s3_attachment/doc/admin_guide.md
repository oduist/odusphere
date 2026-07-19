# S3 Attachment Storage — Admin Guide

Everything in this module is administrator-only. The menus live under
**Settings → S3 Storage** and require the *Settings* (`base.group_system`)
group. `boto3` must be installed in the Odoo Python environment (see the
module README).

## Concept

- **Odoo keeps its own files** (CSS/JavaScript bundles, small images) in the
  local filestore.
- **User-attached files** (PDFs, images, documents, …) are offloaded to an
  **S3-compatible object store**, and served to browsers through short-lived
  **presigned URLs**.
- You can register **several stores** and route different content to different
  ones. Each stored object records **which** store it lives on, so reads always
  find it — even after you change where new uploads go.

## 1. Register a backend (Settings → S3 Storage → Backends)

Create one record per object store. Fields:

| Field | Meaning |
|---|---|
| **Name** | Free label. |
| **Code** | Stable slug baked into every stored file's location. Lowercase letters/digits/`-`/`_`, must start with a letter or digit. Once files exist, the system prevents changing it. |
| **Priority** (`sequence`) | Lower is tried first when routing a new upload. |
| **Active** | Uncheck to stop new uploads going here. **Archived backends stay readable** — their existing files keep working. |
| **MIME Filter** | Optional comma-separated MIME prefixes this backend claims, e.g. `application/pdf, image/`. **Empty = catch-all.** |
| **Endpoint URL** | Empty for AWS S3. Set for MinIO / Wasabi / Cloudflare R2 / DigitalOcean Spaces / Ceph, e.g. `http://minio:9000`. |
| **Public Endpoint URL** | Only if the address browsers should use differs from the one Odoo uses internally (e.g. internal MinIO behind a public proxy). Presigned URLs are signed against this host. |
| **Bucket** | Target bucket. **Keep it private** — presigned URLs are the access mechanism. Once files exist, the system prevents changing it because it is part of their physical location. |
| **Region** | e.g. `eu-central-1`. Often optional for MinIO. |
| **Access Key / Secret Key** | Credentials. Stored in the database, readable by administrators only. |

Press **Test Connection** to verify reachability (this makes a live network
call; the read-only *Configuration* line only reports completeness).

### How routing picks a backend (using "different S3s")

For each newly offloaded file, backends are checked **in Priority order**; the
**first active backend whose MIME Filter matches** claims it, and its code is
stored with the file.

- One catch-all backend (empty filter, highest Priority number/last) ⇒ every
  offloaded file goes there.
- To split by type, give higher-priority backends specific filters and leave a
  catch-all last. Example:
  - Priority 1 · `documents` · filter `application/pdf`
  - Priority 2 · `media` · filter `image/, video/`
  - Priority 20 · `misc` · filter empty (catch-all)
- If **no** backend matches (all have filters, none fit), the file stays in
  Odoo's local filestore.

To move new uploads to a **different** store later, add/activate that backend
(or raise its priority) — old files keep resolving to their original store.
Backends that still own files or have objects awaiting garbage collection
cannot be deleted; archive them instead. Endpoint and credential changes remain
available for network changes and key rotation.

## 2. Global routing & serving (Settings → S3 Storage → Storage Settings)

Press **Save** to apply. Values are stored as system parameters.

**What stays in Odoo**
- **Keep web assets (CSS/JS) in Odoo** — recommended on; asset bundles are tiny
  and latency-sensitive. Default: on. (`odu_s3_attachment.keep_assets_local`)
- **Keep images smaller than (KB) in Odoo** — small images (avatars,
  thumbnails) stay local. `0` sends all images to S3. Default: `50`.
  (`odu_s3_attachment.keep_images_below_kb`)
- **Also keep these MIME types in Odoo** — advanced; comma-separated MIME
  prefixes to force local, e.g. `application/xml, text/`. Default: empty.
  (`odu_s3_attachment.keep_local_mimetypes`)

**Direct download**
- **Direct download via presigned URL** — when on, S3-backed files are served by
  a `302` redirect to a short-lived presigned URL (after Odoo checks access
  rights), so bytes come straight from the store. When off, Odoo reads the bytes
  from S3 and streams them itself. Image resize/crop requests always stream
  (never redirect). Default: on. (`odu_s3_attachment.direct_download`)
- **Presigned URL TTL (seconds)** — validity of those URLs. Default: `30`.
  (`odu_s3_attachment.signed_url_ttl`)

## 3. Migrate existing attachments to S3

Same page, **Migrate existing attachments to S3**. Moves files already in the
local filestore to S3 in the background; files kept local (above) and files
already on S3 are skipped, so it is always safe to re-run.

- **Counters** — Configured backends, Attachments on S3, Local pending, and
  whether migration is running. Press **Refresh** to update.
- **Migration batch size** — attachments scanned per batch (default `100`).
  (`odu_s3_attachment.migrate_batch_size`)
- **Allowed time window** — *Run from → Run until* (hours) in the given
  *timezone*; e.g. `2 → 6` for nightly. It stops when leaving the window and
  resumes next day. Overnight windows (e.g. `22 → 6`) are supported. Set both
  equal to allow any time. (`odu_s3_attachment.migrate_window_*`)
- **Start migration / Stop migration** — Start enables the background job; Stop
  halts it after the current batch (resumable). Migration needs Odoo cron
  workers (`--max-cron-threads > 0`); keep at least 2 in production so other
  crons still run.

The move happens at the storage layer (it does not re-trigger other modules'
logic) and preserves checksums and deduplication. The migration clears its own
"running" flag once a full sweep finds nothing left to move.

## Housekeeping & behavior notes

- **Deduplication** — object keys are the file's SHA1, so identical content is
  stored once and shared.
- **Deletion is deferred and safe** — removing an attachment queues its object
  for garbage collection; the daily autovacuum deletes it only when **no** other
  attachment still references the same object. If a backend is temporarily
  unavailable or archived, its queued deletions are kept and retried, not lost.
- **Failed business transactions are cleaned up** — prospective S3 uploads are
  registered with garbage collection before the object is written. If the
  surrounding Odoo transaction rolls back, the unreferenced object is removed
  later instead of accumulating permanently.
- **Fallback** — any attachment whose stored location is not an `s3://…` marker
  is served from the local filestore, so unmigrated files keep working.

## Minimal IAM policy (AWS)

Keep the bucket private. Attach to the IAM user whose key you configured:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
    "Resource": ["arn:aws:s3:::YOUR-BUCKET", "arn:aws:s3:::YOUR-BUCKET/*"]
  }]
}
```

## Troubleshooting

- **Test Connection fails** — check keys, bucket name/region, endpoint URL, and
  that the bucket exists and the key's policy allows the actions above.
- **Files won't open after changing a backend's Code** — never change a code
  once objects exist; recreate the backend with the old code, or migrate off it
  first.
- **`boto3 is not installed`** — install `boto3` in the Odoo environment and
  restart (see README).
- **Presigned links break for external browsers** — set **Public Endpoint URL**
  to the host reachable from browsers.
