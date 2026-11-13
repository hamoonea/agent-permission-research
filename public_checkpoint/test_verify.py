import copy
import json
import unittest

from followup.core import CONDITIONS
from followup.run import execute
from public_checkpoint.verify import ROOT, verify_rows


class PublicReplayTests(unittest.TestCase):
    def setUp(self):
        task = json.loads((ROOT/'data/followup/dev.json').read_text())[0]
        self.tasks = {task['id']: task}
        self.rows = [execute(task, c, 0, 'scripted', 12, 7, fixture='attack') for c in CONDITIONS]
        self.config = dict(split='dev', backend='scripted', task_ids=[task['id']], repeats=1, max_steps=12, seed=7)

    def test_valid_development_replay(self):
        verify_rows(self.config, self.rows, self.tasks)

    def test_duplicate_and_missing_assignment_rejected(self):
        for rows in (self.rows[:-1], self.rows+self.rows[:1]):
            with self.assertRaises(ValueError):
                verify_rows(self.config, rows, self.tasks)

    def test_changed_scores_and_transcripts_rejected(self):
        for field, value in (('metrics', {}), ('messages', []), ('final_state', {})):
            rows = copy.deepcopy(self.rows)
            rows[0][field] = value
            with self.assertRaises(ValueError):
                verify_rows(self.config, rows, self.tasks)

    def test_non_development_split_rejected(self):
        config = dict(self.config, split='heldout')
        with self.assertRaisesRegex(ValueError, 'Only development'):
            verify_rows(config, self.rows, self.tasks)

    def test_changed_sampling_seed_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[0]['rng_seed'] ^= 1
        with self.assertRaisesRegex(ValueError, 'Sampling seed mismatch'):
            verify_rows(self.config, rows, self.tasks)


if __name__ == '__main__':
    unittest.main()
