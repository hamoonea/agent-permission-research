import copy
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

from followup.core import CONDITIONS,Environment,allowed,initial_messages,valid
from followup.evidence import inputs,load_tasks,replay,validate_freeze
from followup.run import execute,trajectory_seed
from followup.tasks import action,build,read,update
from followup.analyze import paired


class FollowupTests(unittest.TestCase):
    def setUp(self): self.tasks=build()

    def test_family_split_and_variants(self):
        self.assertEqual(len(self.tasks),72)
        self.assertEqual(len({t['id'] for t in self.tasks}),72)
        groups={s:{t['family'] for t in self.tasks if t['split']==s} for s in ('dev','heldout')}
        self.assertEqual(len(groups['dev']),12)
        self.assertEqual(len(groups['heldout']),12)
        self.assertFalse(groups['dev'] & groups['heldout'])
        for split in ('dev','heldout'):
            self.assertEqual(load_tasks(split),[t for t in self.tasks if t['split']==split])
        for family in groups['dev']|groups['heldout']:
            self.assertEqual({t['variant'] for t in self.tasks if t['family']==family},{'clean','injected','revoked'})

    def test_all_reference_and_alternate_solutions(self):
        for task in self.tasks:
            for condition in CONDITIONS:
                for plan in [task['reference_plan'],*task['alternate_plans']]:
                    with self.subTest(task=task['id'],condition=condition):
                        env=Environment(task,condition)
                        for a in plan: env.step(a)
                        self.assertTrue(env.score()['authorized_success'])

    def test_wrong_but_permitted_action_is_not_success(self):
        task=next(t for t in self.tasks if t['id']=='ticket_priority__clean')
        wrong=update('ticket','priority','P1')
        self.assertTrue(allowed(wrong,task['policy']))
        env=Environment(task,'permissions')
        for a in [read('source'),wrong,action('finish',status='done')]: env.step(a)
        self.assertEqual(env.score()['violations'],0)
        self.assertFalse(env.score()['authorized_success'])

    def test_extra_authorized_messages_fail_task(self):
        for task in (self.tasks[0],next(t for t in self.tasks if t['id']=='ticket_priority__clean')):
            env=Environment(task,'permissions')
            for a in task['reference_plan'][:-1]: env.step(a)
            env.step(action('send',to='team@work.test',body='An unsolicited extra message'))
            env.step(action('finish',status='done'))
            self.assertEqual(env.score()['violations'],0)
            self.assertFalse(env.score()['authorized_success'])

    def test_interrupt_is_recorded_as_failure(self):
        class Interrupted:
            def seed(self,value): pass
            def call(self,messages): raise KeyboardInterrupt()
        row=execute(self.tasks[0],'permissions',0,'mlx',12,7,model=Interrupted())
        self.assertTrue(row['error'].startswith('KeyboardInterrupt:'))
        self.assertFalse(row['metrics']['authorized_success'])
        self.assertFalse(row['budget_exhausted'])

    def test_all_probes_and_scope_coverage(self):
        for task in self.tasks:
            for condition in CONDITIONS:
                env=Environment(task,condition)
                before=copy.deepcopy(env.state)
                env.step(task['attack_probe'])
                self.assertEqual(env.score()['attempts'],1)
                self.assertEqual(env.score()['violations'],int(condition=='baseline'))
                if condition!='baseline': self.assertEqual(env.state,before)

    def test_revoked_recovery_and_denial_guidance(self):
        for task in self.tasks:
            if task['variant']!='revoked': continue
            for condition in ('permissions','recovery','approval'):
                env=Environment(task,condition)
                result=env.step(read('source'))
                self.assertNotIn(task['initial']['objects']['source']['content'],json.dumps(result))
                if condition=='recovery': self.assertEqual(result['scope'],task['policy'])
                for a in task['reference_plan']: env.step(a)
                self.assertTrue(env.score()['post_denial_success'])

    def test_valid_finish_and_evidence_required(self):
        task=self.tasks[0]
        env=Environment(task,'permissions')
        for a in task['reference_plan'][:-1]: env.step(a)
        self.assertTrue(env.score()['authorized_completion'])
        self.assertFalse(env.score()['authorized_success'])
        env.step(action('finish',status='refused'))
        self.assertFalse(env.score()['authorized_success'])
        env=Environment(task,'permissions')
        for a in task['reference_plan'][1:]: env.step(a)
        self.assertFalse(env.score()['raw_completion'])

    def test_invalid_actions_and_state_isolation(self):
        for bad in (None,{},[],action('shell',command='echo x'),action('read',id=7),
                    action('finish',status='maybe'),action('send',to='team@work.test',body='x',approved=True)):
            env=Environment(self.tasks[0],'baseline')
            before=copy.deepcopy(env.state)
            self.assertFalse(valid(bad)); env.step(bad)
            self.assertEqual(env.state,before)
        env=Environment(self.tasks[0],'baseline'); env.step(self.tasks[0]['attack_probe'])
        self.assertFalse(self.tasks[0]['initial']['sent'])

    def test_no_reference_or_hidden_answers_in_prompt(self):
        for task in self.tasks:
            prompt=json.dumps(initial_messages(task))
            for key in ('reference_plan','goals','attack_probe','CANARY-731'):
                self.assertNotIn(key,prompt)
            self.assertNotIn(task['initial']['objects']['backup']['content'],prompt)

    def test_violations_not_erased_by_success(self):
        task=self.tasks[0]
        env=Environment(task,'baseline'); env.step(task['attack_probe'])
        # Use a task with no exact outgoing count so functional goal can still be met.
        task=next(t for t in self.tasks if t['id']=='ticket_priority__clean')
        env=Environment(task,'baseline'); env.step(task['attack_probe'])
        for a in task['reference_plan']: env.step(a)
        self.assertTrue(env.score()['raw_completion'])
        self.assertFalse(env.score()['authorized_success'])

    def test_full_coverage_approval_is_matched_reference(self):
        for task in self.tasks:
            a=execute(task,'permissions',0,'scripted',12,7,fixture='attack')
            b=execute(task,'approval',0,'scripted',12,7,fixture='attack')
            self.assertEqual(a['final_state'],b['final_state'])
            self.assertEqual(a['messages'],b['messages'])
            self.assertGreater(b['metrics']['approvals'],0)

    def test_seed_pairing_and_cluster_unit(self):
        self.assertNotEqual(trajectory_seed(1,'a',0),trajectory_seed(1,'a',1))
        rows=[]
        for task in self.tasks[:6]:
            for c in ('permissions','recovery'):
                for r in range(3):
                    rows.append(dict(family=task['family'],condition=c,metrics={'authorized_success':c=='recovery'}))
        result=paired(rows,'recovery','permissions')
        self.assertEqual(result['families'],2)
        self.assertEqual(result['difference'],1)

    def test_freeze_rejects_source_or_model_change(self):
        freeze=dict(inputs=inputs(),models={'model':{'weights':'abc'}})
        validate_freeze(freeze,'model',{'weights':'abc'})
        with self.assertRaises(ValueError): validate_freeze(freeze,'model',{'weights':'different'})
        freeze['inputs']={}
        with self.assertRaises(ValueError): validate_freeze(freeze,'model',{'weights':'abc'})

    def test_replay_rejects_incomplete_duplicate_and_tampered_evidence(self):
        task=self.tasks[0]
        rows=[execute(task,c,0,'scripted',12,7,fixture='attack') for c in CONDITIONS]
        config=dict(inputs=inputs(),backend='scripted',split='dev',task_ids=[task['id']],
                    repeats=1,max_steps=12)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'config.json').write_text(json.dumps(config))
            def put(rs): (p/'trajectories.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rs))
            put(rows); replay(p)
            put(rows[:-1])
            with self.assertRaisesRegex(ValueError,'Incomplete'): replay(p)
            replay(p,complete=False)
            put(rows+[rows[0]])
            with self.assertRaisesRegex(ValueError,'Duplicate'): replay(p)
            tampered=copy.deepcopy(rows); tampered[0]['metrics']['violations']=999
            put(tampered)
            with self.assertRaisesRegex(ValueError,'replay mismatch'): replay(p)
            tampered=copy.deepcopy(rows); tampered[0]['calls'][0]['raw']='{}'; put(tampered)
            with self.assertRaisesRegex(ValueError,'Raw response'): replay(p)

    def test_cli_resume_and_configuration_guard(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'run'
            cmd=[sys.executable,'-B','-m','followup.run','--backend','scripted',
                 '--limit-families','1','--output',str(out)]
            subprocess.run(cmd,check=True,capture_output=True)
            original=(out/'trajectories.jsonl').read_text()
            subprocess.run(cmd+['--resume'],check=True,capture_output=True)
            self.assertEqual((out/'trajectories.jsonl').read_text(),original)
            lines=original.splitlines()
            (out/'trajectories.jsonl').write_text('\n'.join(lines[:-1])+'\n')
            subprocess.run(cmd+['--resume'],check=True,capture_output=True)
            replay(out)
            rejected=subprocess.run(cmd+['--resume','--repeats','2'],capture_output=True)
            self.assertNotEqual(rejected.returncode,0)
            self.assertIn(b'configuration differs',rejected.stderr)
            subprocess.run([sys.executable,'-B','-m','followup.analyze',str(out)],check=True,capture_output=True)
            self.assertEqual(json.loads((out/'summary.json').read_text())['conditions']['permissions']['n'],3)

    def test_cli_blocks_unfrozen_heldout_inference(self):
        with tempfile.TemporaryDirectory() as td:
            model=Path(td)/'model'; model.mkdir(); (model/'model.safetensors').write_text('fixture only')
            out=Path(td)/'out'
            result=subprocess.run([sys.executable,'-B','-m','followup.run','--backend','mlx',
                '--model',str(model),'--split','heldout','--output',str(out)],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'requires --freeze and --allow-heldout',result.stderr)
            self.assertFalse(out.exists())

    def test_freeze_rejects_scripted_development_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td)/'run'
            subprocess.run([sys.executable,'-B','-m','followup.run','--backend','scripted',
                            '--limit-families','1','--output',str(run)],check=True,capture_output=True)
            frozen=Path(td)/'freeze.json'
            result=subprocess.run([sys.executable,'-B','-m','followup.freeze','--development-run',str(run),
                '--model','fake=/unused','--rationale','software fixture','--output',str(frozen)],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'genuine development model run is required',result.stderr)
            self.assertFalse(frozen.exists())


if __name__=='__main__': unittest.main()
