# -*- coding: utf-8 -*-
"""Low-level boto3 helpers shared by the S3 backend records.

Unlike a single-backend design, connection settings are NOT read from
``odoo.conf`` here — each :class:`odu.s3.backend` record carries its own
credentials and passes them in as a plain ``settings`` dict. The boto3 client
objects are cached per process, keyed by the resolved settings, so the
underlying HTTP connection pool is reused across requests and across backends
that happen to share the same endpoint/credentials.
"""
import logging
import threading

_logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.config import Config as BotoConfig
except ImportError:  # pragma: no cover - boto3 is an external dependency
    boto3 = None
    BotoConfig = None

# Whether the boto3 stack is importable in this environment.
HAS_BOTO3 = boto3 is not None

# cache: settings-signature -> boto3 client
_clients = {}
_clients_lock = threading.Lock()


def _endpoint_for(settings, public=False):
    """Resolve the endpoint URL, optionally the public one for presigning."""
    if public and settings.get("public_endpoint_url"):
        return settings["public_endpoint_url"]
    return settings.get("endpoint_url") or None


def _build_client(endpoint_url, settings):
    s3_config = {}
    # Custom endpoints (MinIO, R2, Ceph, ...) require path-style addressing;
    # AWS keeps the default virtual-hosted style.
    if endpoint_url:
        s3_config["addressing_style"] = "path"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or None,
        aws_access_key_id=settings.get("access_key"),
        aws_secret_access_key=settings.get("secret_key"),
        region_name=settings.get("region") or None,
        config=BotoConfig(
            signature_version="s3v4",
            s3=s3_config,
            max_pool_connections=64,
        ),
    )


def get_client(settings, public=False):
    """Return a cached boto3 S3 client for the given ``settings`` dict.

    :param dict settings: keys ``endpoint_url``, ``public_endpoint_url``,
        ``access_key``, ``secret_key``, ``region``.
    :param bool public: when True, sign against ``public_endpoint_url`` (if set)
        so generated presigned URLs point at a host reachable by end-user
        browsers rather than the internal endpoint Odoo talks to.
    """
    if boto3 is None:
        raise RuntimeError(
            "boto3 is not installed; cannot use S3 attachment storage")
    endpoint_url = _endpoint_for(settings, public=public)
    signature = (
        endpoint_url,
        settings.get("access_key"),
        settings.get("secret_key"),
        settings.get("region"),
    )
    client = _clients.get(signature)
    if client is None:
        with _clients_lock:
            client = _clients.get(signature)
            if client is None:
                client = _build_client(endpoint_url, settings)
                _clients[signature] = client
    return client


def upload_dedup(client, bucket, key, data, content_type=None):
    """Upload ``data`` to ``key`` unless the object already exists (dedup).

    boto3 clients are thread-safe, so this helper may be called concurrently.
    Returns True if it actually uploaded, False if the object was already
    present (content-addressed keys make a matching key equivalent content).
    """
    try:
        client.head_object(Bucket=bucket, Key=key)
        return False  # already present -> skip re-upload
    except Exception:
        pass
    extra = {"ContentType": content_type} if content_type else {}
    client.put_object(Bucket=bucket, Key=key, Body=data, **extra)
    return True
