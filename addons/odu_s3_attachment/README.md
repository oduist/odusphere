# odu_s3_attachment — S3 Attachment Storage

Offload user `ir.attachment` binaries to one or more **S3-compatible object
stores** (AWS S3, MinIO, Wasabi, Cloudflare R2, DigitalOcean Spaces, Ceph, …)
and serve them via short-lived **presigned URLs**, while Odoo keeps serving its
own web assets (CSS/JS, small images) locally.

Part of the OduSphere platform — depends on `odu_base`.

## Highlights

- **Multiple backends.** Register several S3 stores; route content to different
  ones by MIME type and priority. Each object remembers its backend in a
  self-describing `store_fname` marker (`s3://<code>/<sha[:2]>/<sha>`), so reads
  always resolve to the right store — including after you change where new
  uploads go, and for archived backends.
- **Transparent routing by mimetype + size.** Everything is offloaded except web
  assets (CSS/JS) and small images, which stay served by Odoo. Rules are
  configurable in *Settings → S3 Storage → Storage Settings*.
- **SHA1 content-addressed keys** ⇒ deduplication, like the native filestore.
- **Automatic fallback.** Non-`s3://` locations are read from the local
  filestore, so unmigrated files keep working.
- **Direct download.** `/web/content` and `/web/image` return a `302` to a
  presigned URL *after* Odoo checks access rights (toggle + TTL configurable).
- **Migration** of existing local attachments via a background, windowed,
  resumable job with row-level concurrency protection (storage-level move;
  dedup preserved).
- **Dedup-aware, rollback-safe, multi-backend garbage collection** of removed
  objects and uploads whose database transaction later rolls back, including
  objects on archived backends.

## Requirements

`boto3` must be installed in the Odoo Python environment (declared in the
manifest `external_dependencies`):

```bash
pip install boto3
```

## Configuration

All configuration is in the UI (administrator-only), under **Settings → S3
Storage**:

1. **Backends** — one record per object store (endpoint, bucket, region,
   access/secret key, optional MIME filter and priority). Credentials are stored
   in the database, readable by administrators only. Press **Test Connection**.
2. **Storage Settings** — what stays in Odoo, direct-download toggle + TTL, and
   the migration console.

See `doc/admin_guide.md` for the full field reference, routing examples, a
minimal AWS IAM policy, and troubleshooting.

## Security

- The bucket stays **private**; presigned URLs are the temporary-access
  mechanism. Access rights are enforced by Odoo before any URL is generated.
- Model access (`odu.s3.backend`, `odu.s3.gc`, `odu.s3.settings`) is restricted
  to the *Settings* group. Internal storage/serving code reaches backends via
  `sudo()`.

## Testing

Routing/marker/window tests run with no S3. The end-to-end suite runs only when
a live S3-compatible backend is provided via environment variables (otherwise it
is skipped):

```
ODU_S3_TEST_ENDPOINT     # e.g. http://minio:9000 (empty for AWS)
ODU_S3_TEST_BUCKET
ODU_S3_TEST_ACCESS_KEY
ODU_S3_TEST_SECRET_KEY
ODU_S3_TEST_REGION       # optional
```
