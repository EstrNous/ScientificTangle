from __future__ import annotations

import datetime
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[1]
TLS_DIR = ROOT / "secrets" / "tls"
FULLCHAIN_PATH = TLS_DIR / "fullchain.pem"
PRIVKEY_PATH = TLS_DIR / "privkey.pem"


def _san_entries(server_name: str) -> list[x509.GeneralName]:
    entries: list[x509.GeneralName] = [x509.DNSName("localhost"), x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]
    try:
        entries.append(x509.IPAddress(ipaddress.ip_address(server_name)))
    except ValueError:
        entries.append(x509.DNSName(server_name))
    return entries


def generate_self_signed_cert(server_name: str = "localhost") -> None:
    TLS_DIR.mkdir(parents=True, exist_ok=True)
    if FULLCHAIN_PATH.is_file() and PRIVKEY_PATH.is_file():
        return
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "RU"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ScientificTangle"),
            x509.NameAttribute(NameOID.COMMON_NAME, server_name),
        ]
    )
    san = x509.SubjectAlternativeName(_san_entries(server_name))
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(san, critical=False)
        .sign(key, hashes.SHA256())
    )
    PRIVKEY_PATH.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    FULLCHAIN_PATH.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))


if __name__ == "__main__":
    import os

    generate_self_signed_cert(os.getenv("NGINX_SERVER_NAME", "localhost"))
