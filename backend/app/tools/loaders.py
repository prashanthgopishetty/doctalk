import asyncio
import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse

import git
from langchain_core.documents import Document

from app.tools.ast_parser import walk_directory

logger = logging.getLogger(__name__)


def _is_github_url(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https"} and "github.com" in parsed.netloc


async def load_github_repo(
    url: str,
    codebase_id: str,
    github_token: str = "",
) -> list[Document]:
    """Clone a public GitHub repo and chunk all supported files.

    Args:
        url: GitHub repository URL (e.g. https://github.com/owner/repo).
        codebase_id: Identifier for the ChromaDB collection.
        github_token: Optional personal access token for authenticated clone.

    Returns:
        List of Document chunks ready for embedding.
    """
    if not _is_github_url(url):
        raise ValueError(f"Not a valid GitHub URL: {url}")

    clone_url = url
    if github_token:
        parsed = urlparse(url)
        clone_url = parsed._replace(netloc=f"{github_token}@{parsed.netloc}").geturl()

    tmp_dir = tempfile.mkdtemp(prefix="doctalk_")
    try:
        logger.info("Cloning %s into %s", url, tmp_dir)
        await asyncio.to_thread(
            git.Repo.clone_from,
            clone_url,
            tmp_dir,
            depth=1,  # shallow clone — faster
        )
        docs = walk_directory(Path(tmp_dir), codebase_id)
        logger.info("Loaded %d chunks from GitHub repo: %s", len(docs), url)
        return docs
    except git.GitCommandError as exc:
        stderr = str(exc.stderr or "").lower()
        stdout = str(exc.stdout or "").lower()
        exc_str = str(exc).lower()
        combined = stderr + stdout + exc_str

        # Auth / access failures — GitHub returns 404 for both private repos AND
        # repos that don't exist (to avoid leaking existence). We treat "not found"
        # without a token as a potential private-repo scenario so the UI can prompt
        # for credentials. With a token already supplied, it's a genuine access denial.
        _auth_keywords = (
            "authentication failed",
            "could not read username",
            "invalid username or password",
            "access denied",
        )
        _not_found_keywords = (
            "not found",       # covers "remote: Not Found" and "repository '...' not found"
            "does not exist",
        )
        _http_errors = ("' 403", "' 401", " 403 ", " 401 ")

        is_auth_error = any(kw in combined for kw in _auth_keywords)
        is_not_found = any(kw in combined for kw in _not_found_keywords)
        is_http_error = any(kw in combined for kw in _http_errors)

        if is_auth_error or is_http_error:
            raise PermissionError(
                "GitHub authentication failed. "
                "Please provide a valid Personal Access Token with 'repo' scope."
            ) from exc

        if is_not_found:
            if github_token:
                # Had a token but still got 404 → repo genuinely inaccessible
                raise PermissionError(
                    "Repository not found or your token does not have access. "
                    "Verify the URL is correct and the token has 'repo' scope."
                ) from exc
            else:
                # No token — could be a private repo (GitHub hides private repos as 404)
                raise PermissionError(
                    "Repository not found. If this is a private repository, "
                    "please provide a Personal Access Token."
                ) from exc

        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def load_local_path(local_path: str, codebase_id: str) -> list[Document]:
    """Walk a local directory and chunk all supported files.

    Args:
        local_path: Absolute or relative path to the directory/file.
        codebase_id: Identifier for the ChromaDB collection.

    Returns:
        List of Document chunks ready for embedding.
    """
    path = Path(local_path).resolve()
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")
    if path.is_file():
        from app.tools.ast_parser import chunk_file
        docs = chunk_file(path, path.parent, codebase_id)
    else:
        docs = walk_directory(path, codebase_id)
    logger.info("Loaded %d chunks from local path: %s", len(docs), path)
    return docs


async def load_uploaded_files(
    file_contents: list[tuple[str, bytes]],
    codebase_id: str,
) -> list[Document]:
    """Process uploaded file bytes and chunk them.

    Args:
        file_contents: List of (filename, content_bytes) tuples.
        codebase_id: Identifier for the ChromaDB collection.

    Returns:
        List of Document chunks ready for embedding.
    """
    tmp_dir = tempfile.mkdtemp(prefix="doctalk_upload_")
    try:
        root = Path(tmp_dir)
        for filename, content in file_contents:
            dest = root / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        docs = walk_directory(root, codebase_id)
        logger.info("Loaded %d chunks from %d uploaded files", len(docs), len(file_contents))
        return docs
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
