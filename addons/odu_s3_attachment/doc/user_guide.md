# S3 Attachment Storage — User Guide

## What this changes for you

Nothing about how you work. You attach files (PDFs, photos, scans, documents)
to records exactly as before, and you open or download them the same way.

Behind the scenes, larger files you attach are kept in cloud object storage
instead of on the Odoo server, while Odoo keeps serving its own small interface
files itself. This is invisible to you — the feature exists so the system stays
fast and its disk stays lean as your OduSphere grows.

## What you might notice

- **Downloads may open from a different web address.** When you download or
  preview a stored file, your browser may be sent straight to the cloud store
  to fetch it. That link is **temporary and personal** — it works for a short
  time right after you click, then stops working. This is normal and keeps your
  files private. If a link you copied earlier no longer opens, just download the
  file again from the record.

- **Everything else is unchanged.** Uploading, replacing, deleting, and viewing
  attachments all behave as usual. Image thumbnails and previews keep their
  normal Odoo dimensions even when the original image is stored in the cloud.

## If a file will not open

Try again from the record itself (do not reuse an old copied link). If it still
fails, contact your administrator — the cloud storage connection is configured
and monitored on the administrator side (see the Admin Guide).
