"""Probe key external hosts for connectivity and print resolved IPs (WireSock hints).

Examples:
    python scripts/check_external_hosts.py
    python scripts/check_external_hosts.py --timeout 5
"""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx

DEFAULT_HOSTS = (
    "torgi.gov.ru",
    "nspd.gov.ru",
    "domclick.ru",
    "avito.ru",
    "cian.ru",
)


def _resolve_ips(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        return [f"resolve_error:{exc}"]
    ips: list[str] = []
    for item in infos:
        sockaddr = item[4]
        if sockaddr:
            ips.append(sockaddr[0])
    return sorted(set(ips))


def _probe_https(host: str, timeout: float) -> tuple[str, int | None]:
    url = f"https://{host}/"
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.head(url)
            return "ok", response.status_code
    except httpx.HTTPError as exc:
        return f"http_error:{type(exc).__name__}", None


def main() -> None:
    parser = argparse.ArgumentParser(description="Check HTTPS reachability and DNS for marketplace / GIS hosts.")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    print(f"timeout={args.timeout}s")
    for host in DEFAULT_HOSTS:
        ips = _resolve_ips(host)
        status, code = _probe_https(host, args.timeout)
        code_part = f" status={code}" if code is not None else ""
        print(f"{host}: {status}{code_part} | ip={', '.join(ips)}")


if __name__ == "__main__":
    main()
