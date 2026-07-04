import argparse
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"
DEFAULT_CREDENTIALS = ROOT / "infra" / "deploy" / "credentials.txt"


def _token(length: int = 24) -> str:
    return secrets.token_urlsafe(length)


def _replace_line(lines: list[str], key: str, value: str) -> None:
    prefix = f"{key}="
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{prefix}{value}"
            return
    lines.append(f"{prefix}{value}")


def _upsert(lines: list[str], key: str, value: str) -> None:
    prefix = f"{key}="
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{prefix}{value}"
            return
    lines.append(f"{prefix}{value}")


def build_env(host: str, *, https: bool, yandex_api_key: str, yandex_folder_id: str) -> tuple[str, dict[str, str]]:
    public_url = f"https://{host}" if https else f"http://{host}"
    postgres_password = _token(18)
    neo4j_password = _token(18)
    minio_password = _token(18)
    internal_token = _token(32)
    grafana_admin_password = _token(16)
    grafana_basic_password = _token(16)

    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    _replace_line(lines, "POSTGRES_PASSWORD", postgres_password)
    _replace_line(lines, "POSTGRES_URL", f"postgresql+asyncpg://st_user:{postgres_password}@postgres:5432/scientific_tangle")
    _replace_line(lines, "AUTH_DATABASE_URL", f"postgresql+asyncpg://st_user:{postgres_password}@postgres:5432/scientific_tangle")
    _upsert(lines, "GATEWAY_DATABASE_URL", f"postgresql+asyncpg://st_user:{postgres_password}@postgres:5432/scientific_tangle")
    _replace_line(lines, "NEO4J_PASSWORD", neo4j_password)
    _replace_line(lines, "NEO4J_AUTH", f"neo4j/{neo4j_password}")
    _replace_line(lines, "MINIO_ROOT_PASSWORD", minio_password)
    _replace_line(lines, "MINIO_SECRET_KEY", minio_password)
    _replace_line(lines, "INTERNAL_SERVICE_TOKEN", internal_token)
    _replace_line(lines, "YANDEX_API_KEY", yandex_api_key)
    _replace_line(lines, "YANDEX_FOLDER_ID", yandex_folder_id)
    _replace_line(lines, "AUTH_ALLOWED_ORIGINS", public_url)
    _replace_line(lines, "AUTH_REFRESH_COOKIE_SECURE", "true" if https else "false")
    _replace_line(lines, "GRAFANA_ADMIN_PASSWORD", grafana_admin_password)
    _replace_line(lines, "GRAFANA_NGINX_BASIC_PASSWORD", grafana_basic_password)
    _upsert(lines, "PUBLIC_HOST", host)
    _upsert(lines, "PUBLIC_URL", public_url)
    _upsert(lines, "NGINX_SERVER_NAME", host)

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
    }
    return "\n".join(lines) + "\n", credentials


def format_credentials(credentials: dict[str, str]) -> str:
    return "\n".join(
        [
            "ScientificTangle — учётные данные после cloud deploy",
            "",
            f"UI:              {credentials['public_url']}/",
            f"API health:      {credentials['public_url']}/api/health",
            f"API health all:  {credentials['public_url']}/api/health/all",
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
    parser.add_argument("--yandex-api-key", default="", help="Yandex Cloud API key for LLM (optional at deploy time)")
    parser.add_argument("--yandex-folder-id", default="", help="Yandex folder ID for LLM (optional at deploy time)")
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

    env_text, credentials = build_env(
        host,
        https=args.https,
        yandex_api_key=args.yandex_api_key.strip(),
        yandex_folder_id=args.yandex_folder_id.strip(),
    )

    output = Path(args.output)
    output.write_text(env_text, encoding="utf-8")

    credentials_path = Path(args.credentials_output)
    credentials_path.parent.mkdir(parents=True, exist_ok=True)
    credentials_path.write_text(format_credentials(credentials), encoding="utf-8")

    print(f"Wrote {output}")
    print(f"Wrote {credentials_path}")
    print(f"PUBLIC_URL={credentials['public_url']}")


if __name__ == "__main__":
    main()
