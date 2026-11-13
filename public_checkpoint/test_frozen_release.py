"""Publication checks do not run model inference or rewrite original artifacts."""
import importlib
from pathlib import Path
import unittest
from unittest.mock import patch

release = importlib.import_module('public_checkpoint.verify')


class FrozenReleaseTests(unittest.TestCase):
    def test_complete_release_preserves_every_failure(self):
        result=release.verify()
        self.assertEqual(result['heldout_trajectories'],432)
        self.assertEqual(result['heldout_unsuccessful_trajectories'],195)
        self.assertEqual(result['failure_trace_sections'],195)
        self.assertEqual(result['development_trajectories_replayed'],432)
        self.assertEqual(result['frozen_inputs_and_snapshots_verified'],13)

    def test_changed_snapshot_rejected(self):
        real_digest=release.digest
        def changed(path):
            if Path(path).as_posix().endswith('followup-heldout-qwen3/source-snapshot/followup/core.py'):
                return 'changed'
            return real_digest(path)
        with patch.object(release,'digest',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'Snapshot input mismatch'):
                release.verify()

    def test_changed_failure_trace_artifact_rejected(self):
        real_digest=release.digest
        with patch.object(release,'digest',side_effect=lambda p:'changed' if Path(p).name=='failure-traces.md' else real_digest(p)):
            with self.assertRaisesRegex(ValueError,'Recorded artifact mismatch'):
                release.verify()


if __name__=='__main__':unittest.main()
