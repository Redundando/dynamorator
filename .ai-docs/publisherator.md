---
Package: publisherator
Version: 0.1.6
Source: https://pypi.org/project/publisherator/
Fetched: 2026-02-21 08:10:30
---

# Publisherator

One-command Python package publishing: bump version, commit, tag, push to GitHub, build, and upload to PyPI.

## Problem

Publishing Python packages requires multiple manual steps: updating version numbers in multiple files, committing changes, creating git tags, pushing to GitHub, building the package, and uploading to PyPI. This repetitive process is error-prone and time-consuming.

## Solution

A lightweight CLI tool that automates the entire publishing workflow with a single command.

## Installation

```bash
pip install publisherator
```

## Usage

```bash
# Bump patch version (1.0.0 → 1.0.1)
publisherator patch

# Bump minor version (1.0.1 → 1.1.0)
publisherator minor

# Bump major version (1.1.0 → 2.0.0)
publisherator major

# Default is patch if no argument provided
publisherator
```

## What It Does

1. ✓ Checks git working directory is clean
2. ✓ Checks git remote 'origin' is configured
3. ✓ Bumps version in `pyproject.toml` and `package/__init__.py`
4. ✓ Commits changes with message "Bump version to X.Y.Z"
5. ✓ Creates git tag `X.Y.Z`
6. ✓ Pushes commits and tags to GitHub
7. ✓ Cleans old build artifacts
8. ✓ Builds package with `python -m build`
9. ✓ Uploads to PyPI with `twine upload`

## Options

```bash
# Preview changes without executing
publisherator patch --dry-run

# Custom commit message
publisherator minor --message "Release new features"
publisherator minor -m "Release new features"

# Skip git operations (only publish to PyPI)
publisherator patch --skip-git

# Skip PyPI upload (only push to git)
publisherator patch --skip-pypi
```

## First-Time Setup

Before using publisherator, ensure:

1. **Git repository initialized**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Git remote configured**
   ```bash
   git remote add origin https://github.com/username/package.git
   ```

3. **PyPI credentials configured**
   - Set up `~/.pypirc` or use environment variables
   - Or configure via `twine` directly

## Requirements

Your package must have:
- `pyproject.toml` with a `version` field
- `package/__init__.py` with `__version__` variable (optional but recommended)

## Error Handling

**Git push fails:** Automatically rolls back commit and tag

**PyPI upload fails:** Provides recovery instructions:
- Retry: `twine upload dist/*`
- Rollback: `git reset --hard HEAD~1 && git tag -d X.Y.Z && git push origin --delete X.Y.Z`

## Features

- ✓ Semantic versioning (major.minor.patch)
- ✓ Multi-file version sync
- ✓ Real-time output streaming for git push, build, and upload
- ✓ Build warning collection and summary
- ✓ Git automation with automatic rollback on push failure
- ✓ Works with any git remote (GitHub, GitLab, Bitbucket, etc.)
- ✓ Supports first-time pushes with automatic upstream tracking
- ✓ Zero configuration needed
- ✓ Helpful error messages and recovery instructions
- ✓ Final summary with GitHub and PyPI URLs

## License

MIT

## Author

Arved Klöhn
