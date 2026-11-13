"""Read and enforce the local inference environment without importing a model."""
import importlib.metadata
import platform
import re
from pathlib import Path

from .tasks import ROOT


def canonical_name(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def runtime_identity(lock_path=None):
    import hashlib
    lock_path = Path(lock_path) if lock_path is not None else ROOT/'requirements-mlx-lock.txt'
    raw = lock_path.read_bytes()
    expected = {}
    for line in raw.decode().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s;]+)', line)
        if not match:
            raise ValueError('Runtime lock must contain exact package==version pins')
        name, version = canonical_name(match[1]), match[2]
        if name in expected:
            raise ValueError('Duplicate package in runtime lock: '+name)
        expected[name] = version
    if not expected:
        raise ValueError('Runtime lock is empty')
    installed = {}
    for distribution in importlib.metadata.distributions():
        name = canonical_name(distribution.metadata['Name'])
        if name in installed:
            raise ValueError('Duplicate installed distribution: '+name)
        installed[name] = distribution.version
    drift = [name for name, version in expected.items() if installed.get(name) != version]
    if drift:
        raise ValueError('Runtime differs from dependency lock: '+', '.join(sorted(drift))+
                         '. Use the original inference environment; do not upgrade during evaluation.')
    return {
        'python_version': platform.python_version(),
        'python_implementation': platform.python_implementation(),
        'platform': platform.platform(),
        'dependency_lock_sha256': hashlib.sha256(raw).hexdigest(),
        'packages': dict(sorted(installed.items())),
    }


def validate_runtime(expected):
    if not isinstance(expected, dict) or not expected:
        raise ValueError('Freeze has no runtime identity; create a verified prospective freeze')
    if expected != runtime_identity():
        raise ValueError('Frozen runtime has changed. Restore the frozen Python, platform, '
                         'dependency lock and installed package versions before evaluation.')
