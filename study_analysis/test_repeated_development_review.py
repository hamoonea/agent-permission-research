import unittest

from followup.core import CONDITIONS
from study_analysis.repeated_development_review import stability,failure_counts


class RepeatReviewTests(unittest.TestCase):
    def test_stability_counts_cases_not_repeats_as_independent_tasks(self):
        rows=[]
        for c in CONDITIONS:
            for task,pattern in [('all',[True,True,True]),('none',[False,False,False]),('mixed',[False,True,False])]:
                rows.extend({'task_id':task,'condition':c,'repeat':i,
                             'metrics':{'authorized_success':success}} for i,success in enumerate(pattern))
        for s in stability(rows).values():
            self.assertEqual(s['always_successful_cases'],1)
            self.assertEqual(s['always_unsuccessful_cases'],1)
            self.assertEqual(s['mixed_outcome_cases'],1)
            self.assertEqual(s['case_success_counts'],{'all':3,'none':0,'mixed':1})

    def test_failure_denominator_keeps_invalid_and_runtime_failures(self):
        rows=[dict(metrics=dict(authorized_success=ok,invalid_actions=invalid,valid_done=done,raw_completion=ok),
                   error=error,budget_exhausted=exhausted,calls=[{},{}],elapsed_seconds=1.5)
              for ok,invalid,done,error,exhausted in [(True,0,True,None,False),(False,2,False,None,True),
                                                     (False,0,False,'RuntimeError: fixture',False)]]
        c=failure_counts(rows)
        self.assertEqual(c['assigned'],3)
        self.assertEqual(c['authorized_success'],1)
        self.assertEqual(c['unsuccessful'],2)
        self.assertEqual(c['invalid_calls'],2)
        self.assertEqual(c['trials_with_invalid_calls'],1)
        self.assertEqual(c['runtime_errors'],1)
        self.assertEqual(c['budget_exhausted'],1)


if __name__=='__main__':unittest.main()
