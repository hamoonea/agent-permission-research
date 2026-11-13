"""Tests use development tasks only; never inspect reserved workflow content."""
import copy
import unittest

from followup.core import Environment
from followup.evidence import load_tasks
from study_analysis.development_audit import diagnose


class DevelopmentAuditTests(unittest.TestCase):
    def setUp(self): self.tasks={t['id']:t for t in load_tasks('dev')}

    def row(self,task,actions,condition='permissions'):
        env=Environment(task,condition)
        for a in actions: env.step(a)
        return dict(condition=condition,repeat=0,metrics=env.score(),events=env.events,
                    final_state=env.state,calls=[{} for _ in env.events],error=None)

    def test_reference_paths_diagnose_no_failure(self):
        for task in self.tasks.values():
            r=self.row(task,task['reference_plan'])
            self.assertEqual(diagnose(task,r)['reasons'],[])

    def test_unsent_draft_sensitivity_does_not_mutate_primary_record(self):
        task=self.tasks['meeting_notice__clean']
        plan=copy.deepcopy(task['reference_plan'])
        draft=copy.deepcopy(plan[1]); draft['tool']='draft'; plan.insert(1,draft)
        r=self.row(task,plan); before=copy.deepcopy(r)
        d=diagnose(task,r)
        self.assertIn('extra_drafts',d['reasons'])
        self.assertFalse(d['success'])
        self.assertTrue(d['posthoc_allow_unsent_drafts_success'])
        self.assertEqual(r,before)

    def test_draft_sensitivity_does_not_forgive_real_sends(self):
        task=self.tasks['meeting_notice__clean']
        plan=copy.deepcopy(task['reference_plan']); plan.insert(1,copy.deepcopy(plan[1]))
        d=diagnose(task,self.row(task,plan))
        self.assertIn('sent_count_mismatch',d['reasons'])
        self.assertFalse(d['posthoc_allow_unsent_drafts_success'])

    def test_draft_sensitivity_does_not_forgive_scope_violation(self):
        task=self.tasks['meeting_notice__clean']
        plan=copy.deepcopy(task['reference_plan'])
        plan.insert(1,{'tool':'draft','args':{'to':'outside@example.test','body':'x'}})
        d=diagnose(task,self.row(task,plan,'baseline'))
        self.assertIn('executed_scope_violation',d['reasons'])
        self.assertFalse(d['posthoc_allow_unsent_drafts_success'])

    def test_wrong_permitted_value_and_regression(self):
        task=self.tasks['ticket_priority__clean']
        plan=copy.deepcopy(task['reference_plan'])
        plan.insert(-1,{'tool':'update','args':{'id':'ticket','field':'priority','value':'P3'}})
        d=diagnose(task,self.row(task,plan))
        self.assertEqual(d['reasons'],['wrong_or_missing_field'])
        self.assertEqual(d['overwritten_correct_fields'],['ticket.priority'])

    def test_order_and_finish_are_distinguished(self):
        task=self.tasks['maintenance_window__clean']
        plan=copy.deepcopy(task['reference_plan'])
        plan[1],plan[2]=plan[2],plan[1]
        d=diagnose(task,self.row(task,plan))
        self.assertEqual(d['reasons'],['message_before_required_update'])
        d=diagnose(task,self.row(task,task['reference_plan'][:-1]))
        self.assertEqual(d['reasons'],['missing_finish_done'])


if __name__=='__main__': unittest.main()
