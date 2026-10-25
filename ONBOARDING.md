# repo-guide — Developer Onboarding

## 1. Project Overview

This repository contains **172 files** identified by RepoGuide's repository scanner.

This document provides an initial overview of the repository, its technology stack, important files, and setup resources.

## 2. Technology Stack

- **Languages:** JavaScript, Python
- **Frontend:** React, Vite
- **Backend:** FastAPI
- **Database:** MongoDB
- **Package Managers:** npm

## 3. Important Files

### `.gitignore`

Files excluded from Git tracking

### `backend/main.py`

Backend application entry point candidate

### `backend/requirements.txt`

Python dependencies

### `frontend/.gitignore`

Files excluded from Git tracking

### `frontend/index.html`

HTML application entry point

### `frontend/package.json`

JavaScript dependencies and scripts

### `frontend/README.md`

Project documentation

### `frontend/src/App.jsx`

Main frontend application component

### `frontend/src/main.jsx`

Frontend application entry point candidate

### `README.md`

Project documentation

### `requests/.gitignore`

Files excluded from Git tracking

### `requests/docs/_themes/.gitignore`

Files excluded from Git tracking

### `requests/docs/requirements.txt`

Python dependencies

### `requests/README.md`

Project documentation

### `requests/tests/certs/expired/README.md`

Project documentation

### `requests/tests/certs/mtls/README.md`

Project documentation

### `requests/tests/certs/README.md`

Project documentation


## 4. Dependencies

### Python Dependencies

- **fastapi** — `==0.149.0`
- **uvicorn** — `[standard]==0.54.0`
- **pymongo** — `==4.19.0`
- **python-dotenv** — `==1.2.4`
- **starlette** — `==1.9.0`
- **pwdlib** — `[argon2]==0.3.1`
- **email-validator** — `==2.3.0`
- **ruff** — `>=0.6,<1.0`
- **radon** — `>=6.0,<7.0`
- **Sphinx** — `==7.2.6`
- **charset_normalizer** — `>=2,<4`
- **idna** — `>=2.5,<4`
- **urllib3** — `>=1.26,<3`
- **certifi** — `>=2023.5.7`

### JavaScript Dependencies

- **react** — `^19.2.8` (dependencies)
- **react-dom** — `^19.2.8` (dependencies)
- **@eslint/js** — `^10.0.1` (devDependencies)
- **@types/react** — `^19.2.18` (devDependencies)
- **@types/react-dom** — `^19.2.7` (devDependencies)
- **@vitejs/plugin-react** — `^6.1.1` (devDependencies)
- **eslint** — `^10.10.0` (devDependencies)
- **eslint-plugin-react-hooks** — `^7.1.1` (devDependencies)
- **eslint-plugin-react-refresh** — `^0.5.6` (devDependencies)
- **globals** — `^17.12.0` (devDependencies)
- **vite** — `^8.3.0` (devDependencies)

## 5. Project Structure

The following files provide a starting point for exploring the repository:

- `.gitignore`
- `backend/main.py`
- `backend/requirements.txt`
- `frontend/.gitignore`
- `frontend/index.html`
- `frontend/package.json`
- `frontend/README.md`
- `frontend/src/App.jsx`
- `frontend/src/main.jsx`
- `README.md`
- `requests/.gitignore`
- `requests/docs/_themes/.gitignore`
- `requests/docs/requirements.txt`
- `requests/README.md`
- `requests/tests/certs/expired/README.md`

## 6. Code Relationships

This section identifies relationships between Python files based on their import statements.

- `backend/main - Copy.py` imports `backend/bug_analyzer.py`
- `backend/main - Copy.py` imports `backend/repository_analyzer.py`
- `backend/main - Copy.py` imports `backend/repository_qa.py`
- `backend/main - Copy.py` imports `backend/repository_quality_analyzer.py`
- `backend/main - Copy.py` imports `requests/src/requests/sessions.py`
- `backend/onboarding_generator.py` imports `backend/documentation_validator.py`
- `backend/onboarding_generator.py` imports `backend/repository_summary.py`
- `backend/quality_checks.py` imports `backend/repository_analyzer.py`
- `backend/repository_analyzer.py` imports `backend/organization_analyzer.py`
- `backend/repository_qa.py` imports `backend/bug_analyzer.py`
- `backend/repository_qa.py` imports `backend/repository_quality_analyzer.py`
- `backend/repository_qa.py` imports `backend/repository_summary.py`
- `backend/repository_quality_analyzer.py` imports `backend/quality_checks.py`
- `backend/repository_quality_analyzer.py` imports `backend/repository_analyzer.py`
- `backend/repository_summary.py` imports `backend/code_relationship_analyzer.py`
- `backend/repository_summary.py` imports `backend/dependency_analyzer.py`
- `backend/repository_summary.py` imports `backend/file_analyzer.py`
- `backend/repository_summary.py` imports `backend/repository_analyzer.py`
- `backend/repository_summary.py` imports `backend/technology_detector.py`
- `backend/technology_detector.py` imports `backend/repository_analyzer.py`
- `backend/test_bug_analyzer.py` imports `backend/bug_analyzer.py`
- `backend/test_code_relationship_analyzer.py` imports `backend/code_relationship_analyzer.py`
- `backend/test_dependency_analyzer.py` imports `backend/dependency_analyzer.py`
- `backend/test_documentation_validator.py` imports `backend/documentation_validator.py`
- `backend/test_file_analyzer.py` imports `backend/file_analyzer.py`
- `backend/test_file_analyzer.py` imports `backend/file_analyzer.py`
- `backend/test_onboarding_generator.py` imports `backend/onboarding_generator.py`
- `backend/test_organization_analyzer.py` imports `backend/organization_analyzer.py`
- `backend/test_quality_checks.py` imports `backend/quality_checks.py`
- `backend/test_repository_analyzer.py` imports `backend/repository_analyzer.py`
- `backend/test_repository_qa.py` imports `backend/repository_qa.py`
- `backend/test_repository_summary.py` imports `backend/repository_summary.py`
- `backend/test_technology_detector.py` imports `backend/technology_detector.py`
- `requests/src/requests/__init__.py` imports `requests/src/requests/__version__.py`
- `requests/src/requests/__init__.py` imports `requests/src/requests/__version__.py`
- `requests/src/requests/__init__.py` imports `requests/src/requests/__version__.py`
- `requests/src/requests/__init__.py` imports `requests/src/requests/__version__.py`
- `requests/src/requests/__init__.py` imports `requests/src/requests/__version__.py`
- `requests/src/requests/__init__.py` imports `requests/src/requests/api.py`
- `requests/src/requests/__init__.py` imports `requests/src/requests/exceptions.py`
- `requests/src/requests/__init__.py` imports `requests/src/requests/exceptions.py`
- `requests/src/requests/__init__.py` imports `requests/src/requests/models.py`
- `requests/src/requests/__init__.py` imports `requests/src/requests/sessions.py`
- `requests/src/requests/__init__.py` imports `requests/src/requests/status_codes.py`
- `requests/src/requests/_internal_utils.py` imports `requests/src/requests/compat.py`
- `requests/src/requests/_types.py` imports `requests/src/requests/auth.py`
- `requests/src/requests/_types.py` imports `requests/src/requests/cookies.py`
- `requests/src/requests/_types.py` imports `requests/src/requests/models.py`
- `requests/src/requests/_types.py` imports `requests/src/requests/structures.py`
- `requests/src/requests/adapters.py` imports `requests/src/requests/__init__.py`
- `requests/src/requests/adapters.py` imports `requests/src/requests/_types.py`
- `requests/src/requests/adapters.py` imports `requests/src/requests/auth.py`
- `requests/src/requests/adapters.py` imports `requests/src/requests/compat.py`
- `requests/src/requests/adapters.py` imports `requests/src/requests/cookies.py`
- `requests/src/requests/adapters.py` imports `requests/src/requests/exceptions.py`
- `requests/src/requests/adapters.py` imports `requests/src/requests/exceptions.py`
- `requests/src/requests/adapters.py` imports `requests/src/requests/models.py`
- `requests/src/requests/adapters.py` imports `requests/src/requests/structures.py`
- `requests/src/requests/adapters.py` imports `requests/src/requests/utils.py`
- `requests/src/requests/api.py` imports `requests/src/requests/__init__.py`
- `requests/src/requests/api.py` imports `requests/src/requests/models.py`
- `requests/src/requests/auth.py` imports `requests/src/requests/_internal_utils.py`
- `requests/src/requests/auth.py` imports `requests/src/requests/compat.py`
- `requests/src/requests/auth.py` imports `requests/src/requests/cookies.py`
- `requests/src/requests/auth.py` imports `requests/src/requests/models.py`
- `requests/src/requests/auth.py` imports `requests/src/requests/utils.py`
- `requests/src/requests/compat.py` imports `requests/src/requests/__version__.py`
- `requests/src/requests/compat.py` imports `requests/src/requests/cookies.py`
- `requests/src/requests/cookies.py` imports `requests/src/requests/_internal_utils.py`
- `requests/src/requests/cookies.py` imports `requests/src/requests/_types.py`
- `requests/src/requests/cookies.py` imports `requests/src/requests/compat.py`
- `requests/src/requests/cookies.py` imports `requests/src/requests/models.py`
- `requests/src/requests/exceptions.py` imports `requests/src/requests/compat.py`
- `requests/src/requests/exceptions.py` imports `requests/src/requests/models.py`
- `requests/src/requests/help.py` imports `requests/src/requests/__init__.py`
- `requests/src/requests/hooks.py` imports `requests/src/requests/__init__.py`
- `requests/src/requests/hooks.py` imports `requests/src/requests/models.py`
- `requests/src/requests/models.py` imports `requests/src/requests/__init__.py`
- `requests/src/requests/models.py` imports `requests/src/requests/_internal_utils.py`
- `requests/src/requests/models.py` imports `requests/src/requests/adapters.py`
- `requests/src/requests/models.py` imports `requests/src/requests/auth.py`
- `requests/src/requests/models.py` imports `requests/src/requests/compat.py`
- `requests/src/requests/models.py` imports `requests/src/requests/cookies.py`
- `requests/src/requests/models.py` imports `requests/src/requests/exceptions.py`
- `requests/src/requests/models.py` imports `requests/src/requests/exceptions.py`
- `requests/src/requests/models.py` imports `requests/src/requests/hooks.py`
- `requests/src/requests/models.py` imports `requests/src/requests/status_codes.py`
- `requests/src/requests/models.py` imports `requests/src/requests/structures.py`
- `requests/src/requests/models.py` imports `requests/src/requests/utils.py`
- `requests/src/requests/packages.py` imports `requests/src/requests/compat.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/__init__.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/_internal_utils.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/_types.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/adapters.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/auth.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/compat.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/cookies.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/exceptions.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/hooks.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/models.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/status_codes.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/structures.py`
- `requests/src/requests/sessions.py` imports `requests/src/requests/utils.py`
- `requests/src/requests/status_codes.py` imports `requests/src/requests/structures.py`
- `requests/src/requests/structures.py` imports `requests/src/requests/compat.py`
- `requests/src/requests/utils.py` imports `requests/src/requests/__init__.py`
- `requests/src/requests/utils.py` imports `requests/src/requests/__version__.py`
- `requests/src/requests/utils.py` imports `requests/src/requests/__version__.py`
- `requests/src/requests/utils.py` imports `requests/src/requests/_internal_utils.py`
- `requests/src/requests/utils.py` imports `requests/src/requests/_types.py`
- `requests/src/requests/utils.py` imports `requests/src/requests/compat.py`
- `requests/src/requests/utils.py` imports `requests/src/requests/cookies.py`
- `requests/src/requests/utils.py` imports `requests/src/requests/exceptions.py`
- `requests/src/requests/utils.py` imports `requests/src/requests/models.py`
- `requests/src/requests/utils.py` imports `requests/src/requests/structures.py`
- `requests/tests/__init__.py` imports `requests/src/requests/exceptions.py`
- `requests/tests/conftest.py` imports `requests/src/requests/compat.py`
- `requests/tests/conftest.py` imports `requests/tests/testserver/server.py`
- `requests/tests/test_adapters.py` imports `requests/src/requests/adapters.py`
- `requests/tests/test_help.py` imports `requests/src/requests/help.py`
- `requests/tests/test_hooks.py` imports `requests/src/requests/hooks.py`
- `requests/tests/test_lowlevel.py` imports `requests/src/requests/compat.py`
- `requests/tests/test_lowlevel.py` imports `requests/tests/testserver/server.py`
- `requests/tests/test_lowlevel.py` imports `requests/tests/utils.py`
- `requests/tests/test_requests.py` imports `requests/src/requests/adapters.py`
- `requests/tests/test_requests.py` imports `requests/src/requests/auth.py`
- `requests/tests/test_requests.py` imports `requests/src/requests/compat.py`
- `requests/tests/test_requests.py` imports `requests/src/requests/cookies.py`
- `requests/tests/test_requests.py` imports `requests/src/requests/exceptions.py`
- `requests/tests/test_requests.py` imports `requests/src/requests/hooks.py`
- `requests/tests/test_requests.py` imports `requests/src/requests/models.py`
- `requests/tests/test_requests.py` imports `requests/src/requests/sessions.py`
- `requests/tests/test_requests.py` imports `requests/src/requests/structures.py`
- `requests/tests/test_requests.py` imports `requests/tests/__init__.py`
- `requests/tests/test_requests.py` imports `requests/tests/compat.py`
- `requests/tests/test_requests.py` imports `requests/tests/testserver/server.py`
- `requests/tests/test_requests.py` imports `requests/tests/utils.py`
- `requests/tests/test_structures.py` imports `requests/src/requests/structures.py`
- `requests/tests/test_testserver.py` imports `requests/tests/testserver/server.py`
- `requests/tests/test_utils.py` imports `requests/src/requests/_internal_utils.py`
- `requests/tests/test_utils.py` imports `requests/src/requests/compat.py`
- `requests/tests/test_utils.py` imports `requests/src/requests/cookies.py`
- `requests/tests/test_utils.py` imports `requests/src/requests/structures.py`
- `requests/tests/test_utils.py` imports `requests/src/requests/utils.py`
- `requests/tests/test_utils.py` imports `requests/tests/compat.py`

**Python files analyzed:** 66
**Relationships detected:** 145

## 7. Setup Guidance

Use the following files to understand how to install and run the project:

- `README.md` or a directory-specific README: check for project instructions.
- `requirements.txt`: inspect Python dependencies.
- `package.json`: inspect JavaScript dependencies and scripts.
- `.env.example`: check which environment variables are required, if this file exists.

Before running the project, review its README and configuration. Install only the dependencies required by the project.

**Note:** This document is generated automatically. Verify the instructions and file descriptions before relying on them.
