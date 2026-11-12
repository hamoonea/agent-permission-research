"""Public checkpoint path shim; the original fixture generator is withheld.

This file was not used to produce the recorded run. See docs/development-checkpoint.md.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    raise SystemExit('Fixture generator withheld until evaluation; see docs/development-checkpoint.md')
