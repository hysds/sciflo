"""Test packaging configuration and metadata."""
import sys
from importlib.metadata import version, requires

import pytest


def test_version_starts_with_7():
    """Verify package version starts with 7."""
    v = version("hysds-sciflo")
    assert v.startswith("7."), f"Expected version 7.x, got {v}"


def test_required_sibling_deps_declared():
    """Verify HySDS sibling dependencies are declared."""
    deps = requires("hysds-sciflo")
    assert deps is not None, "No dependencies found"
    
    dep_names = {dep.split()[0].split(";")[0].split(">=")[0].split("~=")[0].split("<")[0]
                 for dep in deps}
    
    required_siblings = {"hysds-commons"}
    missing = required_siblings - dep_names
    
    assert not missing, f"Missing required HySDS deps: {missing}"


def test_core_modules_importable():
    """Verify core sciflo modules can be imported."""
    import sciflo
    assert hasattr(sciflo, "__version__")


def test_python_version_requirement():
    """Verify running on Python 3.12+."""
    assert sys.version_info >= (3, 12), "Requires Python 3.12+"


def test_package_name_is_hysds_sciflo():
    """Verify package is published as hysds-sciflo."""
    v = version("hysds-sciflo")
    assert v is not None, "Package 'hysds-sciflo' not found"


def test_import_name_is_sciflo():
    """Verify import name remains 'sciflo' (not hysds_sciflo)."""
    import sciflo
    assert sciflo.__name__ == "sciflo"


def test_console_scripts_defined():
    """Verify console scripts are defined."""
    from importlib.metadata import entry_points
    
    scripts = entry_points()
    if hasattr(scripts, 'select'):
        console_scripts = scripts.select(group='console_scripts')
    else:
        console_scripts = scripts.get('console_scripts', [])
    
    script_names = [ep.name for ep in console_scripts]
    
    # Check for some key scripts
    expected_scripts = ["filelist.py", "sflExec", "sciflod"]
    for script in expected_scripts:
        assert script in script_names, f"{script} console script not found"
