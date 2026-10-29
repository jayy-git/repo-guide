import os
import shutil
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
import re
import tempfile
import zipfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request as URLRequest, urlopen

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from starlette.middleware.sessions import SessionMiddleware

from repository_quality_analyzer import analyze_repository_quality
from repository_analyzer import scan_repository
from repository_qa import answer_repository_question
from groq_qa import answer_with_groq
from technology_detector import detect_technology_stack
from bug_analyzer import (
    analyze_python_code,
    analyze_repository_bugs,
    generate_bug_report_markdown,
)

# Load environment variables from backend/.env
env_path = Path(__file__).with_name(".env")
load_dotenv(env_path)

# Read the MongoDB connection string
mongodb_uri = os.getenv("MONGODB_URI")
session_secret = os.getenv("SESSION_SECRET")

if not session_secret:
    raise RuntimeError("SESSION_SECRET is missing from backend/.env")

if not mongodb_uri:
    raise RuntimeError("MONGODB_URI is missing from backend/.env")

# Create a password hasher
password_hasher = PasswordHash.recommended()


# Define the data models for authentication
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Data models for bug and code analysis
class RepoBugAnalysisRequest(BaseModel):
    repository_path: str = "."
    include_ai: bool = False

class RepositoryQuestionRequest(BaseModel):
    repository_path: str = "."
    question: str = Field(min_length=1, max_length=2000)


class SnippetAnalysisRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100_000)
    filename: Optional[str] = Field(default="snippet.py", max_length=200)
    include_ai: Optional[bool] = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create one MongoDB client for the application
    client = MongoClient(mongodb_uri)

    # Check the database connection
    client.admin.command("ping")

    # Make the client available to our API routes
    app.state.mongodb_client = client
    app.state.database = client["hackloop"]

    print("Connected to MongoDB Atlas!")

    try:
        yield
    finally:
        client.close()
        print("MongoDB connection closed.")


app = FastAPI(
    title="RepoGuide API",
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="hackloop_session",
    same_site="lax",
    https_only=os.getenv("COOKIE_HTTPS_ONLY", "false").lower() in {"1", "true", "yes"},
    max_age=3600,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
        ).split(",") if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "RepoGuide API is running!"
    }


@app.post("/auth/register")
def register_user(user: RegisterRequest):
    database = app.state.database
    users = database["users"]
    email = str(user.email).lower().strip()

    existing_user = users.find_one({"email": email})
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists."
        )

    hashed_password = password_hasher.hash(user.password)
    result = users.insert_one({
        "name": user.name,
        "email": email,
        "password_hash": hashed_password,
        "role": "developer"
    })

    return {
        "message": "Account created successfully!",
        "user_id": str(result.inserted_id),
        "email": email
    }


@app.post("/auth/login")
def login_user(request: Request, user: LoginRequest):
    users = app.state.database["users"]
    email = str(user.email).lower().strip()

    existing_user = users.find_one({"email": email})
    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    password_is_valid = password_hasher.verify(
        user.password,
        existing_user["password_hash"]
    )
    if not password_is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    request.session["user_id"] = str(existing_user["_id"])
    request.session["role"] = existing_user["role"]

    return {
        "message": "Login successful!",
        "user_id": str(existing_user["_id"]),
        "email": existing_user["email"],
        "role": existing_user["role"]
    }


@app.post("/auth/logout")
def logout_user(request: Request):
    """Clear the current authenticated session cookie."""
    request.session.clear()
    return {"message": "Logged out successfully."}


@app.get("/auth/me")
def get_current_user(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        return {"logged_in": False, "message": "No active session"}

    return {
        "logged_in": True,
        "user_id": user_id,
        "role": request.session.get("role")
    }


@app.post("/repository/quality-check")
def repository_quality_check(request: Request, repository_path: str):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in before analyzing a repository."
        )

    project_root = Path(__file__).resolve().parent.parent
    target_path = Path(repository_path).resolve()

    if not target_path.is_relative_to(project_root):
        raise HTTPException(
            status_code=403,
            detail="You can only analyze repositories inside the project directory."
        )

    try:
        return analyze_repository_quality(target_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="The repository directory was not found."
        )
    except NotADirectoryError:
        raise HTTPException(
            status_code=400,
            detail="The provided path must be a directory."
        )


MAX_REPOSITORY_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_EXTRACTED_REPOSITORY_BYTES = 200 * 1024 * 1024
MAX_REPOSITORY_FILES = 10000


def _parse_github_repository_url(value: str) -> tuple[str, str]:
    """Validate a public GitHub repository URL and return its owner/repo."""
    parsed = urlparse(value.strip())
    try:
        port = parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="The GitHub URL is invalid.") from exc

    if (
        parsed.scheme.lower() != "https"
        or parsed.hostname not in {"github.com", "www.github.com"}
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise HTTPException(
            status_code=400,
            detail="Enter a public GitHub URL such as https://github.com/owner/repository.",
        )

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2 or parts[0] in {".", ".."}:
        raise HTTPException(
            status_code=400,
            detail="Enter a GitHub repository URL such as https://github.com/owner/repository.",
        )

    owner, repository = parts[0], parts[1]
    repository = repository.removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", owner) or not re.fullmatch(
        r"[A-Za-z0-9_.-]{1,100}", repository
    ):
        raise HTTPException(status_code=400, detail="The GitHub repository URL is invalid.")
    return owner, repository


def _download_github_repository(github_url: str, destination: Path) -> Path:
    """Download and safely extract a public GitHub repository archive."""
    owner, repository = _parse_github_repository_url(github_url)
    archive_url = f"https://api.github.com/repos/{owner}/{repository}/zipball"
    request = URLRequest(
        archive_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "RepoGuide-Repository-Analyzer",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    archive_path = destination / "repository.zip"
    downloaded = 0

    try:
        with urlopen(request, timeout=20) as response, archive_path.open("wb") as archive_file:
            final_url = urlparse(response.geturl())
            if final_url.scheme != "https" or final_url.hostname not in {
                "api.github.com", "codeload.github.com"
            }:
                raise HTTPException(
                    status_code=400,
                    detail="GitHub redirected the download to an unexpected location.",
                )
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > MAX_REPOSITORY_ARCHIVE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="The repository archive exceeds the 100 MB download limit.",
                    )
                archive_file.write(chunk)
    except HTTPException:
        raise
    except HTTPError as exc:
        if exc.code == 404:
            raise HTTPException(
                status_code=404,
                detail="GitHub repository not found. Check the URL and make sure the repository is public.",
            ) from exc
        if exc.code in {401, 403}:
            raise HTTPException(
                status_code=400,
                detail="GitHub could not provide this repository. It may be private or temporarily rate-limited.",
            ) from exc
        raise HTTPException(
            status_code=502, detail=f"GitHub download failed (HTTP {exc.code})."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not reach GitHub. Check your internet connection and try again.",
        ) from exc

    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            if len(members) > MAX_REPOSITORY_FILES:
                raise HTTPException(status_code=413, detail="The repository contains too many files to analyze.")
            extracted_total = 0
            safe_members = []
            for member in members:
                member_path = Path(member.filename)
                # GitHub archives normally have one top-level folder. Reject absolute,
                # parent-traversal, and symlink entries before writing anything.
                normalized = member.filename.replace("\\", "/")
                parts = normalized.split("/")
                if normalized.startswith("/") or any(part in {"", ".", ".."} for part in parts[:-1]):
                    raise HTTPException(status_code=400, detail="The repository archive contains an unsafe path.")
                unix_mode = (member.external_attr >> 16) & 0o170000
                if unix_mode == 0o120000:
                    continue
                if member.file_size > 0 and member.compress_size > 0 and member.file_size / member.compress_size > 1000:
                    raise HTTPException(status_code=413, detail="The repository archive contains a suspiciously compressed file.")
                extracted_total += member.file_size
                if extracted_total > MAX_EXTRACTED_REPOSITORY_BYTES:
                    raise HTTPException(status_code=413, detail="The extracted repository exceeds the 200 MB limit.")
                safe_members.append((member, parts))

            for member, parts in safe_members:
                output_path = destination.joinpath(*parts)
                resolved_output = output_path.resolve()
                if not resolved_output.is_relative_to(destination.resolve()):
                    raise HTTPException(status_code=400, detail="The repository archive contains an unsafe path.")
                if member.is_dir():
                    output_path.mkdir(parents=True, exist_ok=True)
                    continue
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, output_path.open("wb") as target:
                    shutil.copyfileobj(source, target)

            root_dirs = [
                child for child in destination.iterdir()
                if child.is_dir() and child.name != "__MACOSX"
            ]
            if len(root_dirs) != 1:
                raise HTTPException(status_code=400, detail="GitHub returned an unexpected repository archive.")
            return root_dirs[0]
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=502, detail="GitHub returned an invalid repository archive.") from exc


@app.post("/repository/analyze-bugs")
def repository_analyze_bugs(request: Request, payload: RepoBugAnalysisRequest):
    """Analyze either a public GitHub URL or a local project directory."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in before analyzing repository bugs.",
        )

    repository_input = payload.repository_path.strip() or "."
    is_github_url = urlparse(repository_input).scheme.lower() in {"https", "http"}
    project_root = Path(__file__).resolve().parent.parent

    try:
        if is_github_url:
            # Download to a temporary directory; never persist untrusted repository files.
            with tempfile.TemporaryDirectory(prefix="repoguide-") as temp_dir:
                repository_path = _download_github_repository(repository_input, Path(temp_dir))
                results = analyze_repository_bugs(
                    repository_path=str(repository_path),
                    include_ai_explanations=payload.include_ai,
                )
                results["technology_stack"] = detect_technology_stack(str(repository_path))
                results["report_markdown"] = generate_bug_report_markdown(results)
        else:
            path_candidate = Path(repository_input)
            target_path = (
                (project_root / path_candidate).resolve()
                if not path_candidate.is_absolute()
                else path_candidate.resolve()
            )
            if not target_path.is_relative_to(project_root):
                raise HTTPException(
                    status_code=403,
                    detail="You can only analyze local repositories inside the project directory.",
                )
            if not target_path.exists():
                raise HTTPException(status_code=404, detail="The repository directory was not found.")
            if not target_path.is_dir():
                raise HTTPException(status_code=400, detail="The provided path must be a directory.")
            results = analyze_repository_bugs(
                repository_path=str(target_path),
                include_ai_explanations=payload.include_ai,
            )
            results["technology_stack"] = detect_technology_stack(str(target_path))
            results["report_markdown"] = generate_bug_report_markdown(results)
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="The repository or a required source file could not be found.",
        ) from exc
    except NotADirectoryError as exc:
        raise HTTPException(
            status_code=400,
            detail="The supplied repository path is not a directory.",
        ) from exc
    except (zipfile.BadZipFile, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail="The repository could not be read. Check that it contains accessible source files.",
        ) from exc

    # Store history without assuming GitHub repositories live under the local project root.
    history_path = (
        repository_input
        if is_github_url
        else target_path.relative_to(project_root).as_posix() or "."
    )
    app.state.database["scan_history"].insert_one({
        "user_id": user_id,
        "repository_path": history_path,
        "repository_name": results.get("repository_name") or (
            repository_input.rstrip("/").split("/")[-1].removesuffix(".git")
            if is_github_url else target_path.name
        ),
        "scanned_at": datetime.now(timezone.utc),
        "health_score": results.get("health_score"),
        "total_findings": results.get("total_findings", len(results.get("findings", []))),
        "severity_breakdown": results.get("severity_breakdown", {}),
        "total_python_files": results.get("total_python_files", 0),
    })
    return results


@app.post("/repository/ask")
def repository_ask(request: Request, payload: RepositoryQuestionRequest):
    """Answer questions about a repository. Protected by session authentication."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in before asking repository questions."
        )

    repository_input = payload.repository_path.strip() or "."
    is_github_url = urlparse(repository_input).scheme.lower() in {"http", "https"}
    project_root = Path(__file__).resolve().parent.parent

    try:
        if is_github_url:
            # Match the analyzer's supported public-GitHub workflow and keep files temporary.
            with tempfile.TemporaryDirectory(prefix="repoguide-qa-") as temp_dir:
                target_path = _download_github_repository(repository_input, Path(temp_dir))
                fallback = answer_repository_question(str(target_path), payload.question)
                return answer_with_groq(target_path, payload.question, fallback)

        path_candidate = Path(repository_input)
        target_path = (
            (project_root / path_candidate).resolve()
            if not path_candidate.is_absolute()
            else path_candidate.resolve()
        )
        if not target_path.is_relative_to(project_root):
            raise HTTPException(
                status_code=403,
                detail="You can only ask questions about repositories inside the project directory."
            )
        fallback = answer_repository_question(
            repository_path=str(target_path),
            question=payload.question
        )
        return answer_with_groq(
            repository_path=target_path,
            question=payload.question,
            fallback_result=fallback,
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="The repository directory was not found."
        )
    except NotADirectoryError:
        raise HTTPException(
            status_code=400,
            detail="The provided path must be a directory."
        )


@app.post("/code/analyze-snippet")
def code_analyze_snippet(request: Request, payload: SnippetAnalysisRequest):
    """
    Analyzes an individual Python code snippet on the fly.
    Protected by session authentication.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in before analyzing code snippets."
        )

    results = analyze_python_code(
        code_string=payload.code,
        filename=payload.filename or "snippet.py",
        include_ai_explanations=payload.include_ai or False
    )
    return results


@app.post("/repository/download-report")
def download_bug_report(request: Request, payload: RepoBugAnalysisRequest):
    """
    Generates and returns the markdown report content for download.
    Protected by session authentication.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in before downloading reports."
        )

    project_root = Path(__file__).resolve().parent.parent
    path_candidate = Path(payload.repository_path)
    target_path = (project_root / path_candidate).resolve() if not path_candidate.is_absolute() else path_candidate.resolve()

    if not target_path.is_relative_to(project_root):
        raise HTTPException(
            status_code=403,
            detail="You can only export reports inside the project directory."
        )

    results = analyze_repository_bugs(
        repository_path=str(target_path),
        include_ai_explanations=payload.include_ai
    )
    report_md = generate_bug_report_markdown(results)

    return {
        "filename": f"BUG_REPORT_{results['repository_name']}.md",
        "markdown": report_md
    }

@app.get("/repository/files")
def get_repository_files(
    request: Request,
    repository_path: str = ".",
):
    """Return a safe inventory for either a local project path or public GitHub URL."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Please log in before exploring repository files.")

    if urlparse(repository_path).scheme.lower() in {"http", "https"}:
        # The analyzer's GitHub download is temporary, so download again for this request.
        # TemporaryDirectory guarantees cleanup after inventory generation.
        try:
            with tempfile.TemporaryDirectory(prefix="repoguide-files-") as temp_dir:
                repository_root = _download_github_repository(repository_path, Path(temp_dir))
                return scan_repository(str(repository_root))
        except HTTPException:
            raise
        except (OSError, zipfile.BadZipFile) as error:
            raise HTTPException(status_code=400, detail="Could not retrieve the public GitHub repository files.") from error

    project_root = Path(__file__).resolve().parent.parent
    path_candidate = Path(repository_path)
    target_path = ((project_root / path_candidate).resolve() if not path_candidate.is_absolute() else path_candidate.resolve())
    if not target_path.is_relative_to(project_root):
        raise HTTPException(status_code=403, detail="You can only explore repositories inside the project directory.")
    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(status_code=404, detail="Repository directory was not found.")
    try:
        return scan_repository(str(target_path))
    except (FileNotFoundError, NotADirectoryError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/repository/scan-history")
def get_repository_scan_history(request: Request, repository_path: Optional[str] = None, limit: int = 20):
    """Return real scan history for the authenticated user only."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Please log in to view scan history.")

    query = {"user_id": user_id}
    if repository_path:
        project_root = Path(__file__).resolve().parent.parent
        candidate = Path(repository_path)
        target_path = ((project_root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve())
        if not target_path.is_relative_to(project_root):
            raise HTTPException(status_code=403, detail="You can only view history for repositories inside the project directory.")
        query["repository_path"] = target_path.relative_to(project_root).as_posix() or "."

    safe_limit = max(1, min(int(limit), 50))
    records = app.state.database["scan_history"].find(query, {"_id": 0}).sort("scanned_at", -1).limit(safe_limit)
    history = []
    for record in reversed(list(records)):
        scanned_at = record.get("scanned_at")
        history.append({
            "repository_path": record.get("repository_path", "."),
            "repository_name": record.get("repository_name", "Repository"),
            "scanned_at": scanned_at.isoformat() if scanned_at else None,
            "health_score": record.get("health_score"),
            "total_findings": record.get("total_findings", 0),
            "severity_breakdown": record.get("severity_breakdown", {}),
            "total_python_files": record.get("total_python_files", 0),
        })
    return {"history": history}


@app.get("/repository/file-content")
def get_repository_file_content(request: Request, repository_path: str = ".", file_path: str = ""):
    """Return a bounded text file from a local repository or public GitHub repository."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Please log in before opening repository files.")
    if not file_path.strip():
        raise HTTPException(status_code=400, detail="A file path is required.")

    is_github_url = urlparse(repository_path).scheme.lower() in {"http", "https"}
    project_root = Path(__file__).resolve().parent.parent

    # For URL-based browsing, download and inspect within a temporary directory.
    # For local browsing, restrict access to the project's root as before.
    temp_context = tempfile.TemporaryDirectory(prefix="repoguide-file-") if is_github_url else None
    try:
        if is_github_url:
            target_repo = _download_github_repository(repository_path, Path(temp_context.name))
        else:
            repo_candidate = Path(repository_path)
            target_repo = ((project_root / repo_candidate).resolve() if not repo_candidate.is_absolute() else repo_candidate.resolve())
            if not target_repo.is_relative_to(project_root):
                raise HTTPException(status_code=403, detail="You can only explore repositories inside the project directory.")
            if not target_repo.exists() or not target_repo.is_dir():
                raise HTTPException(status_code=404, detail="Repository directory was not found.")

        relative_file = Path(file_path)
        target_file = (target_repo / relative_file).resolve()
        if not target_file.is_relative_to(target_repo):
            raise HTTPException(status_code=403, detail="The requested file is outside the repository.")
        if not target_file.exists() or not target_file.is_file():
            raise HTTPException(status_code=404, detail="File was not found in this repository.")

        blocked_parts = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
        if any(part.lower() in blocked_parts for part in target_file.relative_to(target_repo).parts):
            raise HTTPException(status_code=403, detail="Files in generated or dependency directories cannot be opened.")
        if target_file.name.lower().startswith(".env") or target_file.name.lower() in {"id_rsa", "id_ed25519"} or target_file.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".db", ".sqlite", ".sqlite3", ".exe", ".dll", ".so", ".bin", ".pyc", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip"}:
            raise HTTPException(status_code=403, detail="This file type is not available in the code viewer.")
        if target_file.stat().st_size > 200_000:
            raise HTTPException(status_code=413, detail="This file is too large to display (limit: 200 KB).")
        try:
            content = target_file.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise HTTPException(status_code=415, detail="This is not a UTF-8 text file.") from error
        except OSError as error:
            raise HTTPException(status_code=500, detail="The file could not be read.") from error
        return {"file_path": relative_file.as_posix(), "content": content, "size_bytes": target_file.stat().st_size}
    finally:
        if temp_context is not None:
            temp_context.cleanup()


