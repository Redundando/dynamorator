# Publishing Dynamorator

## Setup (One-Time)

```bash
pip install publisherator
```

Ensure PyPI credentials are configured in `~/.pypirc`.

## Publish New Version

```bash
# Patch release (1.0.0 → 1.0.1)
publisherator patch

# Minor release (1.0.1 → 1.1.0)
publisherator minor

# Major release (1.1.0 → 2.0.0)
publisherator major
```

That's it! Publisherator will:
1. Bump version in `pyproject.toml` and `dynamorator/__init__.py`
2. Commit and tag
3. Push to GitHub
4. Build package
5. Upload to PyPI

## Preview Changes

```bash
publisherator patch --dry-run
```
