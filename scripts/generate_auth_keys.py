from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

secrets_dir = Path(__file__).resolve().parents[1] / "secrets"
secrets_dir.mkdir(exist_ok=True)
private_path = secrets_dir / "auth_private.pem"
public_path = secrets_dir / "auth_public.pem"
for path in (private_path, public_path):
    if path.exists() and path.is_dir():
        import shutil

        shutil.rmtree(path)
if private_path.exists() and private_path.is_file() and public_path.exists() and public_path.is_file():
    raise SystemExit(0)
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
private_path.write_bytes(
    key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
)
public_path.write_bytes(
    key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
)
