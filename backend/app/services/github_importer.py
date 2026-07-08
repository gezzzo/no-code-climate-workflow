from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse, urlunparse
from urllib.request import Request, urlopen

from app.core.config import settings


class GitHubImportError(ValueError):
    pass


@dataclass(frozen=True)
class GitHubFileRef:
    download_url: str
    display_url: str
    filename: str
    repository: str | None = None
    ref: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class ImportedGitHubFile:
    path: Path
    filename: str
    source_url: str
    raw_url: str
    bytes_read: int
    repository: str | None = None
    ref: str | None = None
    file_path: str | None = None


def resolve_github_file_url(source_url: str) -> GitHubFileRef:
    parsed = urlparse(source_url.strip())
    host = parsed.netloc.lower()

    if parsed.scheme != "https":
        raise GitHubImportError("Only HTTPS GitHub file links are supported.")

    if host == "raw.githubusercontent.com":
        return _resolve_raw_github_url(parsed)

    if host in {"github.com", "www.github.com"}:
        return _resolve_github_blob_url(parsed)

    raise GitHubImportError("Use a GitHub file link from github.com or raw.githubusercontent.com.")


def download_github_file(source_url: str) -> ImportedGitHubFile:
    file_ref = resolve_github_file_url(source_url)
    suffix = Path(file_ref.filename).suffix.lower()
    temp_path: Path | None = None
    bytes_read = 0

    request = Request(
        file_ref.download_url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": "Climate-Studio-GitHub-Importer",
        },
    )

    try:
        with urlopen(request, timeout=settings.github_import_timeout_seconds) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > settings.github_import_max_bytes:
                raise GitHubImportError(_max_size_message())

            with tempfile.NamedTemporaryFile("wb", delete=False, suffix=suffix) as temp_file:
                temp_path = Path(temp_file.name)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    bytes_read += len(chunk)
                    if bytes_read > settings.github_import_max_bytes:
                        raise GitHubImportError(_max_size_message())
                    temp_file.write(chunk)
    except HTTPError as exc:
        if exc.code == 404:
            raise GitHubImportError("GitHub file not found. Check the URL and repository visibility.") from exc
        raise GitHubImportError(f"GitHub download failed with status {exc.code}.") from exc
    except URLError as exc:
        raise GitHubImportError(f"Could not reach GitHub: {exc.reason}") from exc
    except TimeoutError as exc:
        raise GitHubImportError("GitHub download timed out. Try again or use a smaller file.") from exc
    except GitHubImportError:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
    except Exception:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise

    if not temp_path:
        raise GitHubImportError("GitHub download did not produce a file.")

    return ImportedGitHubFile(
        path=temp_path,
        filename=file_ref.filename,
        source_url=file_ref.display_url,
        raw_url=file_ref.display_url,
        bytes_read=bytes_read,
        repository=file_ref.repository,
        ref=file_ref.ref,
        file_path=file_ref.path,
    )


def _resolve_raw_github_url(parsed) -> GitHubFileRef:
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 4:
        raise GitHubImportError("Raw GitHub links must include owner, repository, ref, and file path.")

    owner, repo, ref = parts[0], parts[1], parts[2]
    file_path = "/".join(parts[3:])
    filename = _safe_filename(parts[-1])
    display_url = urlunparse(parsed._replace(query="", fragment=""))

    return GitHubFileRef(
        download_url=urlunparse(parsed._replace(fragment="")),
        display_url=display_url,
        filename=filename,
        repository=f"{owner}/{repo}",
        ref=ref,
        path=file_path,
    )


def _resolve_github_blob_url(parsed) -> GitHubFileRef:
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 5 or parts[2] not in {"blob", "raw"}:
        raise GitHubImportError("Use a GitHub file URL such as /owner/repo/blob/main/data.csv.")

    owner, repo, _, ref = parts[0], parts[1], parts[2], parts[3]
    file_parts = parts[4:]
    file_path = "/".join(file_parts)
    filename = _safe_filename(file_parts[-1])
    encoded_path = "/".join(quote(part) for part in [owner, repo, ref, *file_parts])
    raw_url = f"https://raw.githubusercontent.com/{encoded_path}"

    return GitHubFileRef(
        download_url=raw_url,
        display_url=raw_url,
        filename=filename,
        repository=f"{owner}/{repo}",
        ref=ref,
        path=file_path,
    )


def _safe_filename(filename: str) -> str:
    cleaned = Path(unquote(filename)).name.strip()
    cleaned = "".join(char for char in cleaned if char not in '<>:"\\|?*')
    return cleaned or "github-dataset"


def _max_size_message() -> str:
    limit_mb = settings.github_import_max_bytes // (1024 * 1024)
    return f"GitHub file is larger than the {limit_mb} MB import limit."
