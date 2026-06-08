from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

from munk.config.schema import MunkConfig

DEFAULT_NO_PROXY_HOSTS: tuple[str, ...] = ("localhost", "127.0.0.1", "::1")


@dataclass(frozen=True)
class ResolvedProxyConfig:
    enabled: bool
    url: str | None
    no_proxy: tuple[str, ...]


def resolve_proxy_config(config: MunkConfig | None) -> ResolvedProxyConfig | None:
    if config is None or config.proxy is None:
        return None
    url = _string_or_none(config.proxy.url)
    return ResolvedProxyConfig(
        enabled=bool(config.proxy.enabled and url),
        url=url,
        no_proxy=tuple(_normalize_no_proxy_entries(config.proxy.no_proxy)),
    )


def build_httpx_proxy_kwargs(*, url: str, proxy: ResolvedProxyConfig | None) -> dict[str, Any]:
    if proxy is None or not proxy.enabled or proxy.url is None:
        return {"trust_env": False}
    if should_bypass_proxy(url, proxy):
        return {"trust_env": False}
    return {
        "proxy": proxy.url,
        "trust_env": False,
    }


def should_bypass_proxy(url: str, proxy: ResolvedProxyConfig | None) -> bool:
    hostname = urlsplit(url).hostname
    if hostname is None:
        return False
    host = hostname.strip().strip("[]")
    if _is_loopback_host(host):
        return True
    if proxy is None:
        return False
    host_lower = host.lower()
    for entry in _effective_no_proxy_entries(proxy):
        if entry == "*":
            return True
        if host_lower == entry:
            return True
        if host_lower.endswith(f".{entry.lstrip('.')}"):
            return True
    return False


def _effective_no_proxy_entries(proxy: ResolvedProxyConfig) -> tuple[str, ...]:
    merged = list(DEFAULT_NO_PROXY_HOSTS)
    merged.extend(proxy.no_proxy)
    return tuple(_normalize_no_proxy_entries(merged))


def _normalize_no_proxy_entries(values: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = _string_or_none(value)
        if normalized is None:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _is_loopback_host(hostname: str) -> bool:
    host = hostname.lower()
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def _string_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
