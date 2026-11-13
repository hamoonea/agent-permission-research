"""Supplemental report checks using only development-based software fixtures."""
import copy
import unittest
from unittest.mock import patch

from followup.core import CONDITIONS
from followup.evidence import load_tasks
from followup.run import execute
from study_analysis.development_audit import diagnose
from study_analysis.heldout_review import build_review, pair_details, review


class HeldoutReportTests(unittest.TestCase):
    def setUp(self):
        tasks=load_tasks('dev')[:6]
        self.tasks={t['id']:t for t in tasks}
        self.rows=[execute(t,c,r,'scripted',12,7,fixture='attack')
                   for t in tasks for c in CONDITIONS for r in range(3)]
        self.audited=[diagnose(self.tasks[r['task_id']],r) for r in self.rows]

    def test_repeat_family_denominators_and_all_failures_preserved(self):
        before=copy.deepcopy(self.rows)
        result=build_review({'repeats':3},self.rows,self.tasks,self.audited)
        self.assertEqual(result['failure_accounting']['assigned'],72)
        self.assertEqual(result['failure_accounting']['unsuccessful'],18)
        self.assertEqual(result['failure_accounting']['authorized_success'],54)
        for arms in result['repeat_summary'].values():
            self.assertTrue(all(arm['n']==6 for arm in arms.values()))
        for family in result['family_results'].values():
            self.assertTrue(all(arm['n']==9 for arm in family['conditions'].values()))
        self.assertEqual(result['family_cluster_recovery_comparison']['families'],2)
        self.assertEqual(result['permission_approval_mismatches'],[])
        self.assertEqual(self.rows,before)

    def test_discordance_uses_task_and_repeat(self):
        rows=copy.deepcopy(self.rows); audited=copy.deepcopy(self.audited)
        key=(rows[0]['task_id'],'recovery',2)
        target=next(r for r in rows if (r['task_id'],r['condition'],r['repeat'])==key)
        diagnosis=next(r for r in audited if (r['task_id'],r['condition'],r['repeat'])==key)
        target['metrics']['authorized_success']=False
        diagnosis['success']=False;diagnosis['reasons']=['test_fixture_failure']
        result=pair_details(rows,audited)
        self.assertEqual(len(result['recovery_discordant_pairs']),1)
        self.assertEqual(result['recovery_discordant_pairs'][0]['repeat'],2)
        self.assertEqual(result['recovery_discordant_pairs'][0]['recovery_reasons'],['test_fixture_failure'])

    def test_incomplete_run_rejected_before_any_reporting(self):
        with patch('study_analysis.heldout_review.replay',side_effect=ValueError('Incomplete run')):
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                review('/unused','/unused')


if __name__=='__main__':unittest.main()
