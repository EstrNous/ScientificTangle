import argparse
import os
import secrets
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"
DEFAULT_CREDENTIALS = ROOT / "infra" / "deploy" / "credentials.txt"


def _token(length: int = 24) -> str:
    return secrets.token_urlsafe(length)


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        result[key.strip()] = value
    return result


def _first_nonempty(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def _replace_line(lines: list[str], key: str, value: str) -> None:
    prefix = f"{key}="
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{prefix}{value}"
            return
    lines.append(f"{prefix}{value}")


def _upsert(lines: list[str], key: str, value: str) -> None:
    _replace_line(lines, key, value)


def public_base_url(host: str, *, https: bool, http_port: int, https_port: int) -> str:
    scheme = "https" if https else "http"
    port = https_port if https else http_port
    default_port = 443 if https else 80
    if port == default_port:
        return f"{scheme}://{host}"
    return f"{scheme}://{host}:{port}"


def build_auth_origins(
    host: str,
    *,
    https: bool,
    http_port: int,
    https_port: int,
    expose_ports: bool,
) -> str:
    origins = [public_base_url(host, https=https, http_port=http_port, https_port=https_port)]
    if expose_ports:
        scheme = "https" if https else "http"
        for port in (3000, 8000, 8001):
            origins.append(f"{scheme}://{host}:{port}")
    unique: list[str] = []
    seen: set[str] = set()
    for origin in origins:
        if origin not in seen:
            seen.add(origin)
            unique.append(origin)
    return ",".join(unique)


def postgres_async_url(password: str) -> str:
    return f"postgresql+asyncpg://st_user:{quote(password, safe='')}@postgres:5432/scientific_tangle"


def build_env(
    host: str,
    *,
    https: bool,
    yandex_api_key: str,
    yandex_folder_id: str,
    http_port: int = 80,
    https_port: int = 443,
    expose_ports: bool = False,
    existing_env: dict[str, str] | None = None,
) -> tuple[str, dict[str, str]]:
    existing = existing_env or {}
    yandex_api_key = _first_nonempty(
        yandex_api_key,
        os.getenv("YANDEX_API_KEY"),
        existing.get("YANDEX_API_KEY"),
    )
    yandex_folder_id = _first_nonempty(
        yandex_folder_id,
        os.getenv("YANDEX_FOLDER_ID"),
        existing.get("YANDEX_FOLDER_ID"),
    )

    public_url = public_base_url(host, https=https, http_port=http_port, https_port=https_port)
    postgres_password = existing.get("POSTGRES_PASSWORD") or _token(18)
    neo4j_password = existing.get("NEO4J_PASSWORD") or _token(18)
    minio_password = existing.get("MINIO_ROOT_PASSWORD") or existing.get("MINIO_SECRET_KEY") or _token(18)
    internal_token = existing.get("INTERNAL_SERVICE_TOKEN") or _token(32)
    grafana_admin_password = existing.get("GRAFANA_ADMIN_PASSWORD") or _token(16)
    grafana_basic_password = existing.get("GRAFANA_NGINX_BASIC_PASSWORD") or _token(16)

    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    _replace_line(lines, "POSTGRES_PASSWORD", postgres_password)
    postgres_url = postgres_async_url(postgres_password)
    _replace_line(lines, "POSTGRES_URL", postgres_url)
    _replace_line(lines, "AUTH_DATABASE_URL", postgres_url)
    _upsert(lines, "GATEWAY_DATABASE_URL", postgres_url)
    _replace_line(lines, "NEO4J_PASSWORD", neo4j_password)
    _replace_line(lines, "NEO4J_AUTH", f"neo4j/{neo4j_password}")
    _replace_line(lines, "MINIO_ROOT_PASSWORD", minio_password)
    _replace_line(lines, "MINIO_SECRET_KEY", minio_password)
    _replace_line(lines, "INTERNAL_SERVICE_TOKEN", internal_token)
    if yandex_api_key:
        _replace_line(lines, "YANDEX_API_KEY", yandex_api_key)
    elif "YANDEX_API_KEY" in existing:
        _replace_line(lines, "YANDEX_API_KEY", existing["YANDEX_API_KEY"])
    if yandex_folder_id:
        _replace_line(lines, "YANDEX_FOLDER_ID", yandex_folder_id)
    elif "YANDEX_FOLDER_ID" in existing:
        _replace_line(lines, "YANDEX_FOLDER_ID", existing["YANDEX_FOLDER_ID"])
    _replace_line(lines, "AUTH_ALLOWED_ORIGINS", build_auth_origins(
        host,
        https=https,
        http_port=http_port,
        https_port=https_port,
        expose_ports=expose_ports,
    ))
    _replace_line(lines, "AUTH_REFRESH_COOKIE_SECURE", "true" if https else "false")
    _replace_line(lines, "GRAFANA_ADMIN_PASSWORD", grafana_admin_password)
    _replace_line(lines, "GRAFANA_NGINX_BASIC_PASSWORD", grafana_basic_password)
    _upsert(lines, "PUBLIC_HOST", host)
    _upsert(lines, "PUBLIC_URL", public_url)
    _upsert(lines, "NGINX_SERVER_NAME", host)
    _upsert(lines, "NGINX_HTTP_PORT", str(http_port))
    _upsert(lines, "NGINX_HTTPS_PORT", str(https_port))
    _upsert(lines, "CLOUD_EXPOSE_PORTS", "true" if expose_ports else "false")

    credentials = {
        "public_url": public_url,
        "public_host": host,
        "admin_username": "admin",
        "admin_password": "admin12345",
        "researcher_username": "researcher",
        "researcher_password": "researcher123",
        "grafana_url": f"{public_url}/grafana/",
        "grafana_admin_user": "admin",
        "grafana_admin_password": grafana_admin_password,
        "grafana_nginx_basic_user": "grafana",
        "grafana_nginx_basic_password": grafana_basic_password,
        "postgres_user": "st_user",
        "postgres_password": postgres_password,
        "neo4j_user": "neo4j",
        "neo4j_password": neo4j_password,
        "minio_root_user": "minioadmin",
        "minio_root_password": minio_password,
        "internal_service_token": internal_token,
        "yandex_configured": bool(yandex_api_key and yandex_folder_id),
    }
    return "\n".join(lines) + "\n", credentials


def format_credentials(credentials: dict[str, str]) -> str:
    yandex_line = (
        "Yandex AI:       настроен (ключ и folder id в .env)"
        if credentials.get("yandex_configured")
        else "Yandex AI:       НЕ настроен — индексация будет в degraded-режиме"
    )
    return "\n".join(
        [
            "ScientificTangle — учётные данные после cloud deploy",
            "",
            f"UI:              {credentials['public_url']}/",
            f"API health:      {credentials['public_url']}/api/health",
            f"API health all:  {credentials['public_url']}/api/health/all",
            "",
            yandex_line,
            "",
            "Вход в UI (seed users):",
            f"  admin:      {credentials['admin_username']} / {credentials['admin_password']}",
            f"  researcher: {credentials['researcher_username']} / {credentials['researcher_password']}",
            "",
            "Grafana:",
            f"  URL:        {credentials['grafana_url']}",
            f"  Grafana:    {credentials['grafana_admin_user']} / {credentials['grafana_admin_password']}",
            f"  nginx auth: {credentials['grafana_nginx_basic_user']} / {credentials['grafana_nginx_basic_password']}",
            "",
            "Инфраструктура (только внутри VM, порты закрыты снаружи):",
            f"  PostgreSQL: {credentials['postgres_user']} / {credentials['postgres_password']}",
            f"  Neo4j:      {credentials['neo4j_user']} / {credentials['neo4j_password']}",
            f"  MinIO:      {credentials['minio_root_user']} / {credentials['minio_root_password']}",
            f"  INTERNAL_SERVICE_TOKEN: {credentials['internal_service_token']}",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate .env for cloud deploy from public host/IP")
    parser.add_argument("--host", required=True, help="Public IP or domain, e.g. 203.0.113.10")
    parser.add_argument("--https", action="store_true", help="Use https:// in PUBLIC_URL and secure cookies")
    parser.add_argument("--yandex-api-key", default="", help="Yandex Cloud API key for LLM")
    parser.add_argument("--yandex-folder-id", default="", help="Yandex folder ID for LLM")
    parser.add_argument("--http-port", type=int, default=80, help="Published nginx HTTP port (default: 80)")
    parser.add_argument("--https-port", type=int, default=443, help="Published nginx HTTPS port (default: 443)")
    parser.add_argument("--expose-ports", action="store_true", help="Publish service ports (postgres, gateway, ui, …)")
    parser.add_argument("--output", default=str(ROOT / ".env"), help="Path to write .env")
    parser.add_argument(
        "--credentials-output",
        default=str(DEFAULT_CREDENTIALS),
        help="Path to write operator credentials card",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    host = args.host.strip().removeprefix("http://").removeprefix("https://").rstrip("/")
    if not host:
        raise SystemExit("host is empty")

    output = Path(args.output)
    existing_env = _read_env_file(output)

    env_text, credentials = build_env(
        host,
        https=args.https,
        yandex_api_key=args.yandex_api_key.strip(),
        yandex_folder_id=args.yandex_folder_id.strip(),
        http_port=args.http_port,
        https_port=args.https_port,
        expose_ports=args.expose_ports,
        existing_env=existing_env,
    )

    output.write_text(env_text, encoding="utf-8")

    credentials_path = Path(args.credentials_output)
    credentials_path.parent.mkdir(parents=True, exist_ok=True)
    credentials_path.write_text(format_credentials(credentials), encoding="utf-8")

    print(f"Wrote {output}")
    print(f"Wrote {credentials_path}")
    print(f"PUBLIC_URL={credentials['public_url']}")
    print(f"YANDEX_CONFIGURED={'yes' if credentials['yandex_configured'] else 'no'}")


if __name__ == "__main__":
    main()
