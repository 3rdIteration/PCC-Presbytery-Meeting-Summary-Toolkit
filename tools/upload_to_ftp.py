"""
upload_to_ftp.py
================

Upload the generated meeting summary `index.html` to an FTP(S) server,
placing it inside a date-named subfolder (e.g. `meetings/2026-05-19/index.html`).

Designed for a non-technical user: reads its server URL (and optionally
username/password) from `ftp_config.json` and prompts interactively for
anything missing. Prefers FTPS (FTP over TLS) and refuses to silently fall
back to unencrypted FTP — the user must confirm. Verifies the server's TLS
certificate against the system trust store; on a verification failure shows
the certificate details and the SHA-256 fingerprint, and (with the user's
explicit OK) pins that fingerprint in the config for future runs.

Configuration
-------------

Create `ftp_config.json` next to this script (or in the meeting folder).
See `ftp_config.example.json` for a starter file.

Schema:
    {
      "url": "ftps://ftp.example.com/public_html/meetings",   # required
      "username": "",                                          # optional; prompted if empty
      "password": "",                                          # optional; prompted if empty (leave empty for safety)
      "public_url_template": "https://example.com/meetings/{date}/",  # optional; printed after upload
      "trusted_cert_fingerprints": []                          # auto-populated when you trust a non-CA cert
    }

URL scheme rules:
    ftps:// or ftpes://  →  TLS required; no plaintext fallback.
    ftp://               →  TLS attempted; on failure prompts before falling back.

Usage
-----

Recommended (toolkit run from outside the meeting folder):

    python <toolkit>/tools/upload_to_ftp.py --folder "<meeting folder path>" --date 2026-05-26

When `--folder` is given:
    - `--file` defaults to `<folder>/index.html`
    - `--date`, if not passed, is auto-detected from the folder name (YYYY-MM-DD)

Legacy (running from inside the meeting folder):

    python tools/upload_to_ftp.py                       # cwd is the meeting folder
    python tools/upload_to_ftp.py --date 2026-05-26     # explicit date (use the meeting's actual date, not the folder name)
    python tools/upload_to_ftp.py --file Summary.html   # upload a different file
    python tools/upload_to_ftp.py --test                # connect + login, no upload
    python tools/upload_to_ftp.py --yes                 # skip the final "proceed with upload?" prompt

By default the script always asks "Proceed with upload?" once it has connected,
logged in, and resolved the remote path — so the user can review the target
before anything is sent. Pass --yes to suppress that prompt (only do this when
the user has already confirmed upstream, e.g. in the agent conversation).
"""

from __future__ import annotations

import argparse
import datetime
import ftplib
import getpass
import hashlib
import json
import re
import socket
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, unquote


CONFIG_FILENAME = "ftp_config.json"
EXAMPLE_FILENAME = "ftp_config.example.json"

# Files we will NEVER upload (credentials / secrets). Hard refusal, no override.
SENSITIVE_BASENAMES = {"ftp_config.json", "ftp_config.example.json"}

# Files that look like toolkit content rather than meeting documents.
# Uploading is allowed only after an explicit prompt confirmation.
TOOLKIT_BASENAMES_CI = {"agents.md", "claude.md", "readme.md"}
TOOLKIT_PARENT_DIRS = {"tools"}


def _info(msg: str) -> None:
    print(msg, flush=True)


def _warn(msg: str) -> None:
    print(f"\n[!] {msg}", file=sys.stderr, flush=True)


def _err(msg: str) -> None:
    print(f"\n[ERROR] {msg}", file=sys.stderr, flush=True)


def _confirm(question: str, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        resp = input(f"{question} {suffix} ").strip().lower()
    except EOFError:
        return default
    if not resp:
        return default
    return resp in ("y", "yes")


def find_config(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    here = Path(__file__).resolve().parent
    candidates = [
        Path.cwd() / CONFIG_FILENAME,
        here / CONFIG_FILENAME,
        here.parent / CONFIG_FILENAME,
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(path: Path, cfg: dict[str, Any]) -> None:
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def detect_meeting_date(folder: Path) -> str | None:
    """Look for a YYYY-MM-DD pattern in the folder name."""
    m = re.search(r"\d{4}-\d{2}-\d{2}", folder.name)
    return m.group(0) if m else None


def parse_target_url(url: str) -> tuple[str, str, int, str, str | None, str | None]:
    """Return (scheme, host, port, base_path, url_user, url_pass)."""
    parsed = urlparse(url)
    scheme = (parsed.scheme or "ftps").lower()
    if scheme not in ("ftp", "ftps", "ftpes"):
        raise ValueError(f"unsupported URL scheme: {scheme!r} (use ftp:// or ftps://)")
    if not parsed.hostname:
        raise ValueError("URL is missing a hostname")
    host = parsed.hostname
    # Default port: 21 for FTP and explicit FTPS (AUTH TLS upgrade); 990 if user opts into implicit FTPS.
    port = parsed.port or 21
    base_path = parsed.path or "/"
    return scheme, host, port, base_path, parsed.username, (unquote(parsed.password) if parsed.password else None)


def cert_summary(cert: dict | None, der: bytes) -> str:
    fp = hashlib.sha256(der).hexdigest()
    lines = [f"  SHA-256 fingerprint: {fp}"]
    if cert:
        subject = dict(x[0] for x in cert.get("subject", []))
        issuer = dict(x[0] for x in cert.get("issuer", []))
        lines.append(f"  Subject: CN={subject.get('commonName','?')} O={subject.get('organizationName','?')}")
        lines.append(f"  Issuer:  CN={issuer.get('commonName','?')} O={issuer.get('organizationName','?')}")
        if subject == issuer:
            lines.append("  Note: Subject equals Issuer (self-signed certificate).")
        not_after = cert.get("notAfter")
        if not_after:
            lines.append(f"  Expires: {not_after}")
            try:
                exp = datetime.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                days_left = (exp - datetime.datetime.utcnow()).days
                if days_left < 30:
                    lines.append(f"  ⚠ Certificate expires in {days_left} day(s).")
            except ValueError:
                pass
        sans = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]
        if sans:
            lines.append(f"  SANs:    {', '.join(sans[:5])}{'…' if len(sans) > 5 else ''}")
    return "\n".join(lines)


def _connect_tls_no_verify(host: str, port: int, timeout: int = 30) -> ftplib.FTP_TLS:
    """Connect with TLS but skip verification — only used after explicit user trust."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ftp = ftplib.FTP_TLS(context=ctx, timeout=timeout)
    ftp.connect(host, port, timeout=timeout)
    ftp.auth()
    return ftp


def connect(
    scheme: str,
    host: str,
    port: int,
    cfg: dict[str, Any],
    cfg_path: Path,
    allow_plain_fallback: bool,
) -> tuple[ftplib.FTP, bool]:
    """Return (connected client, used_tls).

    Raises SystemExit on user refusal to proceed under any condition.
    """
    require_tls = scheme in ("ftps", "ftpes")
    trusted_fps: set[str] = set(cfg.get("trusted_cert_fingerprints", []) or [])

    # Attempt TLS first (for all schemes — ftp:// will downgrade on failure if user permits).
    try:
        ssl_ctx = ssl.create_default_context()
        ftp = ftplib.FTP_TLS(context=ssl_ctx, timeout=30)
        ftp.connect(host, port, timeout=30)
        ftp.auth()
        _info(f"  TLS established (verified): {ftp.sock.version()}, cipher={ftp.sock.cipher()[0]}")
        return ftp, True
    except ssl.SSLCertVerificationError as e:
        _warn(f"TLS certificate verification FAILED: {e.reason or e}")
        # Reconnect insecurely to inspect the actual certificate.
        try:
            ftp_ins = _connect_tls_no_verify(host, port)
        except Exception as e2:
            _err(f"Could not retrieve server certificate for inspection: {e2}")
            raise SystemExit(4)
        cert = ftp_ins.sock.getpeercert()
        der = ftp_ins.sock.getpeercert(binary_form=True)
        fp = hashlib.sha256(der).hexdigest()
        _warn("Server certificate details:")
        print(cert_summary(cert, der), file=sys.stderr)
        if fp in trusted_fps:
            _info("  ✓ This fingerprint was previously trusted in your config; continuing.")
            return ftp_ins, True
        ftp_ins.close()
        if not _confirm("\nTrust this certificate and continue?"):
            raise SystemExit(3)
        # User trusted it: reconnect insecurely and pin the fingerprint.
        ftp = _connect_tls_no_verify(host, port)
        trusted_fps.add(fp)
        cfg["trusted_cert_fingerprints"] = sorted(trusted_fps)
        save_config(cfg_path, cfg)
        _info(f"  Fingerprint pinned in {cfg_path.name}; future runs won't re-prompt.")
        return ftp, True
    except (ssl.SSLError, ConnectionRefusedError, socket.timeout, OSError,
            ftplib.error_perm, ftplib.error_temp, ftplib.error_proto) as e:
        # error_perm here typically means the server replied "500/530" to AUTH TLS
        # — i.e. it does not speak FTPS at all.
        if isinstance(e, ftplib.Error):
            _warn(f"Server does not appear to support TLS (AUTH TLS rejected: {e}).")
        else:
            _warn(f"TLS connection failed: {e}")
        if require_tls:
            _err("URL scheme requires TLS; refusing to fall back to plaintext.")
            raise SystemExit(4)
        if not allow_plain_fallback:
            if not _confirm("Fall back to PLAIN unencrypted FTP? Credentials will travel in cleartext.", default=False):
                raise SystemExit(4)
        ftp = ftplib.FTP(timeout=30)
        ftp.connect(host, port, timeout=30)
        return ftp, False


def _cwd_or_mkdir(ftp: ftplib.FTP, name: str) -> None:
    """cd into `name`; if it doesn't exist, try to create it then cd in.
    Raises a clear PermissionError-like ftplib.error_perm if creation is denied.
    """
    try:
        ftp.cwd(name)
        return
    except ftplib.error_perm:
        pass
    try:
        ftp.mkd(name)
    except ftplib.error_perm as e:
        raise ftplib.error_perm(
            f"could not create remote directory {name!r}: {e}. "
            f"Check that your account has write permission at this path."
        ) from e
    ftp.cwd(name)


def navigate_and_create(ftp: ftplib.FTP, base_path: str, date: str) -> str:
    """cd to base_path (creating intermediate dirs), then mkdir/cd into the date folder.
    Returns the final remote pwd.
    """
    if base_path and base_path != "/":
        for part in base_path.strip("/").split("/"):
            if part:
                _cwd_or_mkdir(ftp, part)
    _cwd_or_mkdir(ftp, date)
    return ftp.pwd()


def do_upload(args: argparse.Namespace) -> int:
    cfg_path = find_config(args.config)
    if not cfg_path:
        here = Path(__file__).resolve().parent
        example = here / EXAMPLE_FILENAME
        _err("FTP config not found.")
        _info(f"  Create {CONFIG_FILENAME} next to upload_to_ftp.py or in your meeting folder.")
        if example.exists():
            _info(f"  A template is provided at: {example}")
            _info("  Copy it to ftp_config.json and fill in your server URL.")
        return 2
    cfg = load_config(cfg_path)
    _info(f"Using config: {cfg_path}")

    url = cfg.get("url", "").strip()
    if not url:
        _err("Config has no 'url' field. Add one (e.g., \"url\": \"ftps://ftp.example.com/path\").")
        return 2

    try:
        scheme, host, port, base_path, url_user, url_pass = parse_target_url(url)
    except ValueError as e:
        _err(str(e))
        return 2

    username = (cfg.get("username") or url_user or "").strip()
    password = cfg.get("password") or url_pass or ""
    if not username:
        username = input(f"FTP username for {host}: ").strip()
    if not password:
        try:
            password = getpass.getpass(f"FTP password for {username}@{host} (input hidden): ")
        except (EOFError, KeyboardInterrupt):
            _err("No password provided.")
            return 2
    if not username or not password:
        _err("Username and password are both required.")
        return 2

    # Resolve file + date — supports --folder for out-of-folder invocation.
    folder = Path(args.folder).resolve() if args.folder else None
    if folder and not folder.is_dir():
        _err(f"--folder is not a directory: {folder}")
        return 2

    if args.file:
        file_path = Path(args.file).resolve()
    elif folder:
        file_path = folder / "index.html"
    else:
        file_path = Path("index.html").resolve()
    if not args.test and not file_path.exists():
        _err(f"File not found: {file_path}")
        return 2

    # Defense in depth: refuse credential files outright; warn-and-confirm on other toolkit content.
    fname_ci = file_path.name.lower()
    if file_path.name in SENSITIVE_BASENAMES or fname_ci.startswith("ftp_config"):
        _err(f"Refusing to upload {file_path.name}: this is a sensitive toolkit file (may contain FTP credentials). "
             f"This refusal cannot be overridden — pass a different --file.")
        return 7
    looks_toolkit = (
        fname_ci in TOOLKIT_BASENAMES_CI
        or any(part.lower() in TOOLKIT_PARENT_DIRS for part in file_path.parts[:-1])
    )
    if looks_toolkit:
        _warn(f"{file_path.name} looks like a toolkit file (path: {file_path}), not a meeting document.")
        if not args.yes and not _confirm("Are you sure you want to upload this?", default=False):
            _info("Upload cancelled — no toolkit content sent.")
            return 0

    if args.date:
        date = args.date
    else:
        source = folder if folder else Path.cwd()
        date = detect_meeting_date(source)
        if not date:
            _err(f"Could not detect meeting date from folder name {source.name!r}. Pass --date YYYY-MM-DD.")
            return 2
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        _err(f"--date must be in YYYY-MM-DD format (got {date!r}).")
        return 2

    _info(f"Connecting to {host}:{port} ({scheme})...")
    ftp, used_tls = connect(scheme, host, port, cfg, cfg_path, allow_plain_fallback=args.insecure_allow_plain)

    try:
        try:
            ftp.login(username, password)
        except ftplib.error_perm as e:
            _err(f"Login failed: {e}")
            _info("  Check your username and password in ftp_config.json (or re-enter them).")
            return 5
        if isinstance(ftp, ftplib.FTP_TLS):
            ftp.prot_p()  # encrypt data channel too
        _info(f"  Logged in as {username}.")
        if not used_tls:
            _warn("Connection is NOT encrypted. Credentials and data traveled in cleartext.")

        try:
            pwd = navigate_and_create(ftp, base_path, date)
        except ftplib.error_perm as e:
            _err(str(e))
            return 6
        _info(f"  Remote directory: {pwd}")

        if args.test:
            _info("Test mode: connection + login + cd succeeded. Skipping upload.")
            return 0

        size = file_path.stat().st_size
        encryption_note = "encrypted (TLS)" if used_tls else "UNENCRYPTED (plain FTP)"
        _info("")
        _info("Ready to upload:")
        _info(f"  Local file:  {file_path}  ({size:,} bytes)")
        _info(f"  Remote path: {host}:{pwd}/{file_path.name}")
        _info(f"  Connection:  {encryption_note}")
        if not args.yes:
            if not _confirm("Proceed with upload?", default=True):
                _info("Upload cancelled by user. Nothing was sent.")
                return 0

        try:
            with open(file_path, "rb") as fh:
                _info(f"Uploading {file_path.name}...")
                ftp.storbinary(f"STOR {file_path.name}", fh)
        except ftplib.error_perm as e:
            _err(f"Upload denied by server: {e}")
            return 6
        _info(f"  ✓ Upload complete.")
        tmpl = cfg.get("public_url_template")
        if tmpl:
            _info(f"\nPublic URL: {tmpl.format(date=date)}")
        return 0
    finally:
        try:
            ftp.quit()
        except Exception:
            try:
                ftp.close()
            except Exception:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Upload index.html to an FTP(S) server inside a dated subfolder.",
    )
    parser.add_argument("--config", help=f"Path to {CONFIG_FILENAME} (default: auto-discover).")
    parser.add_argument("--folder", help="Path to the meeting folder. When given, --file defaults to <folder>/index.html and --date defaults to the date in the folder name.")
    parser.add_argument("--file", help="File to upload (default: ./index.html, or <folder>/index.html if --folder is given).")
    parser.add_argument("--date", help="Meeting date YYYY-MM-DD (default: detected from --folder, or from cwd folder name).")
    parser.add_argument("--test", action="store_true", help="Connect, log in, and cd — but do not upload.")
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the final upload confirmation prompt (the user already approved upstream).",
    )
    parser.add_argument(
        "--insecure-allow-plain",
        action="store_true",
        help="If TLS is unavailable on an ftp:// server, skip the confirmation prompt and use plain FTP.",
    )
    args = parser.parse_args(argv)
    try:
        return do_upload(args)
    except KeyboardInterrupt:
        _err("Aborted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
