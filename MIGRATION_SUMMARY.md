# HySDS SciFlo Packaging Migration Summary

## Migration Completed: March 24, 2026

This document summarizes the migration of the `sciflo` repository from legacy `setup.py` to modern `pyproject.toml` packaging.

---

## Changes Made

### ✅ Files Created

1. **`pyproject.toml`** - Modern packaging configuration
   - Package name: `hysds-sciflo` (PyPI) / `sciflo` (import)
   - Version: Dynamic from git tags via `hatch-vcs`
   - Dependencies: 6 third-party packages + 1 HySDS sibling
   - Console scripts: 10+ scripts migrated from legacy scripts list

2. **`.github/workflows/publish.yml`** - PyPI publishing automation
   - Triggered on git tags (`v*`)
   - Uses PyPI Trusted Publishers (OIDC)

### ✅ Files Modified

1. **`sciflo/__init__.py`**
   - Added `__version__ = version("hysds-sciflo")` at the top

2. **`setup.py`**
   - Replaced with minimal shim for backward compatibility
   - Delegates all configuration to `pyproject.toml`
   - Will be removed in v7.1.0+

---

## Key Dependency Changes

### Fixed Issues

| Issue | Before | After |
|-------|--------|-------|
| Missing hysds-commons | Not declared | `hysds-commons~=7.0` |

### Dependencies Preserved Exactly

All 6 core dependencies maintained with exact pins from original `setup.py`:
- `twisted>=18.9.0`
- `pillow>=5.4.1`
- `formencode>=1.3.1`
- `sqlobject>=3.7.1`
- `service_identity>=18.1.0`
- `python-magic>=0.4.15`

### Console Scripts Migrated

Legacy shell scripts converted to Python entry points:
- `filelist.py`
- `subsetAeronet.py`
- `hdfMetadata.py`
- `sflExec`
- `ldapSearch`
- `ldapAuth`
- `insertDataFromXml`
- `crawlAll`
- `getConfigVal`
- `sciflod`

---

## Build Verification

```bash
$ python -m build
Successfully built hysds_sciflo-1.5.0.post1.dev0+g3fb2be084.d20260324.tar.gz
Successfully built hysds_sciflo-1.5.0.post1.dev0+g3fb2be084.d20260324-py3-none-any.whl
```

---

## Next Steps

### Before Publishing to PyPI

1. **Verify hysds-commons published first**
   - ✅ `hysds-commons~=7.0` must be on PyPI

2. **Tag version 7.0.0**
   ```bash
   git tag -a v7.0.0 -m "Release 7.0.0 - Modern packaging migration"
   git push origin v7.0.0
   ```

3. **Configure PyPI Trusted Publisher**
   - Go to https://pypi.org/manage/account/publishing/
   - Add GitHub Actions publisher for `hysds/sciflo` repo
   - Workflow: `publish.yml`
   - Environment: `pypi`

### Installation Methods

#### Development (Local)
```bash
pip install -e .
```

#### Development (From Git Branch)
```bash
pip install "git+https://github.com/hysds/sciflo.git@feature-branch"
```

#### Production (After PyPI Publishing)
```bash
pip install hysds-sciflo

# Console scripts still work
filelist.py --help
sflExec --help
```

---

## Backward Compatibility

### Import Names (Unchanged)
```python
# All existing imports continue to work
import sciflo
from sciflo.grid import Grid
```

### Console Scripts (Preserved)
All legacy scripts now available as Python entry points.

### Package Name Change
- **PyPI package**: `sciflo` → `hysds-sciflo`
- **Import name**: `sciflo` (unchanged)

---

## Migration Checklist

- [x] Create `pyproject.toml` with all dependencies
- [x] Add missing hysds-commons dependency
- [x] Preserve all other dependency pins exactly
- [x] Update `sciflo/__init__.py` for dynamic versioning
- [x] Migrate legacy scripts to console entry points
- [x] Add GitHub Actions workflow for PyPI publishing
- [x] Keep minimal `setup.py` shim for backward compatibility
- [x] Verify `python -m build` succeeds
- [ ] Tag v7.0.0 release
- [ ] Configure PyPI Trusted Publisher
- [ ] Publish to PyPI

---

## Contact

For questions about this migration, contact the HySDS team at hysds-help@jpl.nasa.gov
