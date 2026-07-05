from pathlib import Path

from scripts.generate_cloud_env import build_env


def test_credentials_use_existing_auth_seed_passwords(tmp_path: Path) -> None:
    existing_env = {
        "AUTH_SEED_ADMIN_USERNAME": "cloud-admin",
        "AUTH_SEED_ADMIN_PASSWORD": "cloud-secret",
        "AUTH_SEED_RESEARCHER_USERNAME": "cloud-researcher",
        "AUTH_SEED_RESEARCHER_PASSWORD": "researcher-secret",
    }
    _, credentials = build_env(
        "203.0.113.10",
        https=False,
        yandex_api_key="",
        yandex_folder_id="",
        existing_env=existing_env,
    )
    assert credentials["admin_username"] == "cloud-admin"
    assert credentials["admin_password"] == "cloud-secret"
    assert credentials["researcher_username"] == "cloud-researcher"
    assert credentials["researcher_password"] == "researcher-secret"
