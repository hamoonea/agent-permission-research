"""Freeze/verification regressions using development records and disposable fixtures."""
import contextlib
import copy
import importlib.metadata
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from followup import freeze, run, runtime, transition
from followup.core import CONDITIONS, Environment
from followup.evidence import ROOT, digest, inputs, load_tasks, replay, validate_freeze, verify_rows

DEV_RUN = ROOT/'outputs/followup-dev-v2-repeats3'


def transition_manifest():
    config = json.loads((DEV_RUN/'config.json').read_text())
    return dict(scope='verification-only; no experimental behavior changes',
                development_config_sha256=digest(DEV_RUN/'config.json'),
                development_trajectories_sha256=digest(DEV_RUN/'trajectories.jsonl'),
                original_inputs=config['inputs'], candidate_inputs=inputs())


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.task = load_tasks('dev')[0]
        self.tasks = {self.task['id']: self.task}
        self.rows = [run.execute(self.task, c, r, 'scripted', 12, 7, fixture='attack')
                     for c in CONDITIONS for r in range(3)]
        self.config = dict(split='dev', backend='scripted', task_ids=list(self.tasks),
                           seed=7, repeats=3, max_steps=12)

    def test_all_repeats_pass_seed_validation(self):
        verify_rows(self.config, self.rows, self.tasks)

    def test_changed_missing_or_invalid_seed_rejected(self):
        for value in (self.rows[0]['rng_seed'] ^ 1, None, True):
            rows = copy.deepcopy(self.rows)
            rows[0]['rng_seed'] = value
            with self.assertRaisesRegex(ValueError, 'Sampling seed mismatch'):
                verify_rows(self.config, rows, self.tasks)
        config = dict(self.config)
        del config['seed']
        with self.assertRaisesRegex(ValueError, 'base sampling seed'):
            verify_rows(config, self.rows, self.tasks)

    def test_private_replay_rejects_altered_seed(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            (directory/'config.json').write_text(json.dumps(dict(self.config, inputs=inputs())))
            rows = copy.deepcopy(self.rows)
            rows[0]['rng_seed'] ^= 1
            (directory/'trajectories.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            with self.assertRaisesRegex(ValueError, 'Sampling seed mismatch'):
                replay(directory)

    def test_missing_duplicate_and_unknown_assignments_rejected(self):
        for rows in (self.rows[:-1], self.rows+self.rows[:1]):
            with self.assertRaises(ValueError):
                verify_rows(self.config, rows, self.tasks)
        for ids in ([self.task['id']]*2, ['unknown']):
            with self.assertRaises(ValueError):
                verify_rows(dict(self.config, task_ids=ids), self.rows, self.tasks)

    def test_seed_checks_also_apply_to_partial_resume(self):
        rows = copy.deepcopy(self.rows[:1])
        verify_rows(self.config, rows, self.tasks, complete=False)
        rows[0]['rng_seed'] ^= 1
        with self.assertRaisesRegex(ValueError, 'Sampling seed mismatch'):
            verify_rows(self.config, rows, self.tasks, complete=False)

    def test_scoring_requires_source_access_but_not_every_reference_read(self):
        task = next(t for t in load_tasks('dev') if t['id']=='budget_balance__clean')
        env = Environment(task, 'permissions')
        for action in task['reference_plan']:
            if action != {'tool':'read', 'args':{'id':'ledger'}}:
                env.step(action)
        self.assertTrue(env.score()['authorized_success'])
        env = Environment(task, 'permissions')
        for action in task['reference_plan']:
            if action['tool'] != 'read':
                env.step(action)
        self.assertFalse(env.score()['authorized_success'])


class RuntimeTests(unittest.TestCase):
    def test_identity_captures_python_platform_lock_and_all_installed_versions(self):
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td)/'lock.txt'
            lock.write_text('Example_Package==1.2\n')
            installed = [SimpleNamespace(metadata={'Name':'example-package'}, version='1.2'),
                         SimpleNamespace(metadata={'Name':'extra'}, version='3.0')]
            with patch.object(importlib.metadata, 'distributions', return_value=installed):
                result = runtime.runtime_identity(lock)
            self.assertEqual(result['dependency_lock_sha256'], digest(lock))
            self.assertEqual(result['packages'], {'example-package':'1.2', 'extra':'3.0'})
            self.assertTrue(result['python_version'] and result['python_implementation'] and result['platform'])

    def test_changed_missing_and_duplicate_dependencies_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td)/'lock.txt'; lock.write_text('example==1.2\n')
            distribution = SimpleNamespace(metadata={'Name':'example'}, version='9.0')
            for installed in ([], [distribution], [distribution, distribution]):
                with patch.object(importlib.metadata, 'distributions', return_value=installed):
                    with self.assertRaises(ValueError):
                        runtime.runtime_identity(lock)

    def test_unpinned_empty_and_duplicate_lock_entries_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td)/'lock.txt'
            for contents in ('example>=1.2', '', 'example==1.2\nexample==1.2'):
                lock.write_text(contents)
                with self.assertRaises(ValueError):
                    runtime.runtime_identity(lock)

    def test_freeze_rejects_runtime_drift_before_loading_tasks_or_model(self):
        actual = dict(python_version='3.13.2', python_implementation='CPython', platform='fixture',
                      dependency_lock_sha256='lock', packages={'mlx':'1', 'tokenizers':'2'})
        altered = []
        for key in ('python_version', 'python_implementation', 'platform', 'dependency_lock_sha256', 'packages'):
            item = copy.deepcopy(actual); item[key] = 'changed'; altered.append(item)
        altered.append(None)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); frozen = root/'freeze.json'; output = root/'out'
            for expected in altered:
                frozen.write_text(json.dumps(dict(inputs=inputs(), models={'qwen3-4b':{'weight':'fixture'}}, runtime=expected)))
                argv = ['followup.run', '--backend', 'mlx', '--model', td, '--split', 'heldout',
                        '--freeze', str(frozen), '--allow-heldout', '--output', str(output)]
                with patch.object(sys, 'argv', argv), patch.object(run, 'model_identity', return_value={'weight':'fixture'}), \
                     patch.object(runtime, 'runtime_identity', return_value=actual), \
                     patch.object(run, 'load_tasks') as loader, patch.object(run, 'MLX') as model:
                    with self.assertRaisesRegex(ValueError, 'runtime'):
                        run.main()
                    loader.assert_not_called(); model.assert_not_called()
                self.assertFalse(output.exists())
                self.assertFalse(list(root.glob('*.started.json')))

    def test_matching_runtime_source_and_model_accepted(self):
        identity = {'fixture':'runtime'}
        frozen = dict(inputs=inputs(), models={'fixture':{'weights':'same'}}, runtime=identity)
        with patch.object(runtime, 'runtime_identity', return_value=identity):
            validate_freeze(frozen, 'fixture', {'weights':'same'})


class TransitionTests(unittest.TestCase):
    def call_transition(self, manifest):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'transition.json'; path.write_text(json.dumps(manifest))
            return transition.replay_development_transition(DEV_RUN, path)

    def test_archived_and_current_replay_pass_without_rewriting_old_inputs(self):
        _, rows, receipt = self.call_transition(transition_manifest())
        self.assertEqual(len(rows), 432)
        self.assertEqual(receipt['sampling_seeds_verified'], 432)
        with self.assertRaisesRegex(ValueError, 'inputs changed'):
            replay(DEV_RUN)

    def test_unreviewed_current_input_drift_rejected(self):
        manifest = transition_manifest(); manifest['candidate_inputs']['followup/run.py'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'commitments'):
            self.call_transition(manifest)

    def test_changed_experimental_input_rejected_even_if_manifest_matches(self):
        manifest = transition_manifest()
        manifest['candidate_inputs']['followup/core.py'] = 'changed'
        with patch.object(transition, 'inputs', return_value=manifest['candidate_inputs']):
            with self.assertRaisesRegex(ValueError, 'Experimental input changed'):
                self.call_transition(manifest)

    def test_changed_archive_or_behavior_rejected(self):
        original_digest = transition.digest
        target = DEV_RUN/'source-snapshot/followup/core.py'
        with patch.object(transition, 'digest', side_effect=lambda p:'changed' if Path(p)==target else original_digest(p)):
            with self.assertRaisesRegex(ValueError, 'snapshot changed'):
                self.call_transition(transition_manifest())
        original_definition = transition.definition
        with patch.object(transition, 'definition', side_effect=lambda p,n:'changed' if p==ROOT/'followup/run.py' and n=='MLX' else original_definition(p,n)):
            with self.assertRaisesRegex(ValueError, 'Experimental behavior changed'):
                self.call_transition(transition_manifest())

    def test_altered_row_or_evidence_commitment_rejected(self):
        manifest = transition_manifest(); manifest['development_trajectories_sha256'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'evidence commitment'):
            self.call_transition(manifest)
        rows = transition.read_rows(DEV_RUN); rows[0]['rng_seed'] ^= 1
        with patch.object(transition, 'read_rows', return_value=rows):
            with self.assertRaisesRegex(ValueError, 'Sampling seed mismatch'):
                self.call_transition(transition_manifest())

    def test_disposable_freeze_records_runtime_and_transition_and_refuses_overwrite(self):
        config = json.loads((DEV_RUN/'config.json').read_text())
        identity = {'packages':config['packages'], 'fixture':'runtime'}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); manifest = root/'transition.json'; frozen = root/'freeze.json'
            manifest.write_text(json.dumps(transition_manifest()))
            argv = ['followup.freeze', '--development-run', str(DEV_RUN), '--development-transition', str(manifest),
                    '--model', 'qwen3-4b='+td, '--output', str(frozen), '--rationale', 'Disposable software test only']
            with patch.object(sys, 'argv', argv), patch.object(freeze, 'runtime_identity', return_value=identity), \
                 patch.object(freeze, 'model_identity', return_value=config['model_files']), contextlib.redirect_stdout(io.StringIO()):
                freeze.main()
                record = json.loads(frozen.read_text())
                self.assertEqual(record['runtime'], identity)
                self.assertEqual(record['development_transition']['current_replay_records'], 432)
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    freeze.main()


if __name__ == '__main__':
    unittest.main()
