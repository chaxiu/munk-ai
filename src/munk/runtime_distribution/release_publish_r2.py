from __future__ import annotations

import hashlib
import hmac
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .release_publish_models import R2PublishConfig, UploadObject


def upload_object(*, config: R2PublishConfig, upload: UploadObject) -> None:
    timestamp = datetime.now(tz=timezone.utc)
    request = build_signed_put_request(
        config=config,
        key=upload.key,
        body=upload.body,
        content_type=upload.content_type,
        cache_control=upload.cache_control,
        timestamp=timestamp,
    )
    try:
        with urllib.request.urlopen(request) as response:  # noqa: S310
            status_code = getattr(response, "status", None)
            if status_code not in {200, 201}:
                raise RuntimeError(f"unexpected upload status for {upload.key}: {status_code}")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"failed to upload R2 object {upload.key}: {exc}") from exc


def build_signed_put_request(
    *,
    config: R2PublishConfig,
    key: str,
    body: bytes,
    content_type: str,
    cache_control: str,
    timestamp: datetime,
) -> urllib.request.Request:
    canonical_path = _build_canonical_path(bucket_name=config.bucket_name, key=key)
    amz_date = timestamp.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = timestamp.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(body).hexdigest()
    host = urllib.parse.urlparse(config.endpoint).netloc
    canonical_headers = (
        f"cache-control:{cache_control}\n"
        f"content-type:{content_type}\n"
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "cache-control;content-type;host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        [
            "PUT",
            canonical_path,
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    credential_scope = f"{date_stamp}/{config.region}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signing_key = _derive_signing_key(config.secret_access_key, date_stamp, config.region, "s3")
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        "AWS4-HMAC-SHA256 "
        f"Credential={config.access_key_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )
    return urllib.request.Request(
        url=f"{config.endpoint}{canonical_path}",
        data=body,
        method="PUT",
        headers={
            "Authorization": authorization,
            "Cache-Control": cache_control,
            "Content-Length": str(len(body)),
            "Content-Type": content_type,
            "Host": host,
            "X-Amz-Content-SHA256": payload_hash,
            "X-Amz-Date": amz_date,
        },
    )


def _build_canonical_path(*, bucket_name: str, key: str) -> str:
    path_parts = [bucket_name, *key.strip("/").split("/")]
    return "/" + "/".join(urllib.parse.quote(part, safe="") for part in path_parts)


def _derive_signing_key(secret_access_key: str, date_stamp: str, region: str, service: str) -> bytes:
    key_date = _sign_bytes(("AWS4" + secret_access_key).encode("utf-8"), date_stamp)
    key_region = _sign_bytes(key_date, region)
    key_service = _sign_bytes(key_region, service)
    return _sign_bytes(key_service, "aws4_request")


def _sign_bytes(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()
