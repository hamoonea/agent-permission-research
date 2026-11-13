"""Development-only regression checks; no reserved data is loaded or generated."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest

from followup.core import CONDITIONS,Environment,SCHEMA_HELP,initial_messages
from followup.evidence import inputs,load_tasks,replay
from followup.run import execute,make_jobs,trajectory_seed


class AmendmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks=load_tasks('dev')
        cls.by_id={t['id']:t for t in cls.tasks}

    def run_plan(self,task,plan,condition='permissions'):
        env=Environment(task,condition)
        for a in plan: env.step(a)
        return env

    def test_every_development_reference_and_alternative_still_succeeds(self):
        for task in self.tasks:
            for condition in CONDITIONS:
                for plan in [task['reference_plan'],*task['alternate_plans']]:
                    with self.subTest(task=task['id'],condition=condition):
                        self.assertTrue(self.run_plan(task,plan,condition).score()['authorized_success'])

    def test_intermediate_draft_allowed_but_send_is_required(self):
        task=self.by_id['meeting_notice__clean']
        plan=copy.deepcopy(task['reference_plan'])
        draft=copy.deepcopy(plan[1]); draft['tool']='draft'
        self.assertTrue(self.run_plan(task,[plan[0],draft,*plan[1:]]).score()['authorized_success'])
        self.assertFalse(self.run_plan(task,[plan[0],draft,plan[-1]]).score()['authorized_success'])

    def test_extra_or_wrong_actual_sends_still_fail(self):
        task=self.by_id['meeting_notice__clean']; plan=copy.deepcopy(task['reference_plan'])
        self.assertFalse(self.run_plan(task,[*plan[:-1],plan[1],plan[-1]]).score()['authorized_success'])
        plan[1]['args']['body']='Wrong delivered content'
        self.assertFalse(self.run_plan(task,plan).score()['authorized_success'])

    def test_explicit_draft_constraint_is_not_relaxed(self):
        task=copy.deepcopy(self.by_id['meeting_notice__clean'])
        task['goals'].append({'kind':'count','collection':'drafts','value':0})
        plan=copy.deepcopy(task['reference_plan']); draft=copy.deepcopy(plan[1]); draft['tool']='draft'
        self.assertFalse(self.run_plan(task,[plan[0],draft,*plan[1:]]).score()['authorized_success'])
        self.assertTrue(self.run_plan(task,plan).score()['authorized_success'])

    def test_draft_only_task_still_requires_draft_and_no_send(self):
        task=self.by_id['contact_draft__clean']; plan=copy.deepcopy(task['reference_plan'])
        self.assertTrue(self.run_plan(task,plan).score()['authorized_success'])
        send=copy.deepcopy(next(a for a in plan if a['tool']=='draft')); send['tool']='send'
        self.assertFalse(self.run_plan(task,[*plan[:-1],send,plan[-1]]).score()['authorized_success'])
        self.assertFalse(self.run_plan(task,[a for a in plan if a['tool']!='draft']).score()['authorized_success'])

    def test_unauthorized_draft_not_forgiven(self):
        task=self.by_id['meeting_notice__clean']; plan=copy.deepcopy(task['reference_plan'])
        draft={'tool':'draft','args':{'to':'outside@example.test','body':'x'}}
        env=self.run_plan(task,[plan[0],draft,*plan[1:]],'baseline')
        self.assertEqual(env.score()['violations'],1)
        self.assertFalse(env.score()['authorized_success'])

    def test_schema_feedback_equal_across_conditions_and_does_not_mutate(self):
        task=self.tasks[0]
        for bad in (None,{'tool':'update','args':{'id':'x','quantity':'16'}},
                    {'tool':'finish','args':{'status':'blocked'}}):
            results=[]
            for condition in CONDITIONS:
                env=Environment(task,condition); before=copy.deepcopy(env.state)
                results.append(env.step(bad))
                self.assertEqual(env.state,before)
                self.assertFalse(env.closed)
                self.assertEqual(env.score()['invalid_actions'],1)
            self.assertTrue(all(r==results[0] for r in results))
            self.assertEqual(results[0]['schema'],SCHEMA_HELP)
            self.assertNotIn('goals',results[0]['schema'])

    def test_permission_approval_match_for_all_development_probes(self):
        for task in self.tasks:
            a=execute(task,'permissions',0,'scripted',12,7,fixture='attack')
            b=execute(task,'approval',0,'scripted',12,7,fixture='attack')
            self.assertEqual(a['messages'],b['messages'])
            self.assertEqual(a['final_state'],b['final_state'])
            self.assertEqual(a['metrics']['violations'],0)

    def test_three_repeat_schedule_and_seed_pairing(self):
        jobs=make_jobs(self.tasks,3,20261111)
        self.assertEqual(len(jobs),432)
        self.assertEqual(len({(t['id'],c,r) for t,c,r in jobs}),432)
        self.assertEqual(jobs,make_jobs(self.tasks,3,20261111))
        self.assertEqual(len({trajectory_seed(20261111,self.tasks[0]['id'],r) for r in range(3)}),3)

    def test_development_only_generator_matches_saved_data(self):
        # Prune the held-out construction before executing any generator code.
        path=Path(__file__).resolve().parents[1]/'followup/tasks.py'
        module=ast.parse(path.read_text())
        module.body=[n for n in module.body if not isinstance(n,ast.If)]
        fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='families')
        assignment=next(n for n in fn.body if isinstance(n,ast.Assign)
                        and any(isinstance(t,ast.Name) and t.id=='dev' for t in n.targets))
        fn.body=[assignment,ast.parse("return {'dev': dev}").body[0]]
        ast.fix_missing_locations(module)
        scope={'__file__':str(path),'__name__':'development_only_fixture_test'}
        exec(compile(module,str(path),'exec'),scope)
        self.assertEqual(scope['build'](),self.tasks)

    def test_replay_keeps_three_repeat_assignments_and_rejects_missing_rows(self):
        task=self.tasks[0]
        rows=[execute(task,c,r,'scripted',12,20261111,fixture='attack') for c in CONDITIONS for r in range(3)]
        config=dict(inputs=inputs(),backend='scripted',split='dev',task_ids=[task['id']],repeats=3,max_steps=12,seed=20261111)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'config.json').write_text(json.dumps(config))
            record=p/'trajectories.jsonl'
            record.write_text(''.join(json.dumps(r)+'\n' for r in rows)); replay(p)
            record.write_text(''.join(json.dumps(r)+'\n' for r in rows[:-1]))
            with self.assertRaisesRegex(ValueError,'Incomplete'): replay(p)


if __name__=='__main__': unittest.main()
