import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ekf.core import Repository, Problem, serialize
from ekf.seed import init_repo


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.main=Path(self.temp.name)/'repo'
        init_repo(self.main,demo=True); self.r=Repository(self.main)

    def tearDown(self):
        self.temp.cleanup()

    def edit(self, text, identity='REQ-SAFE-001'):
        a=self.r.artifact(identity)
        return self.r.save(a['path'],a['raw']+'\n'+text+'\n',a['hash'])

    def external_main(self, path, text):
        target=self.main/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(text)
        self.r.git('add','--',path,cwd=self.main)
        self.r.git('commit','-m','External main update',cwd=self.main)

    def test_edits_accumulate_in_isolated_persistent_draft(self):
        before=self.r.head(); original=self.r.artifact('REQ-SAFE-001')
        first=self.edit('First edit'); identity=self.r.workflow.active
        self.edit('Second edit')
        self.assertEqual(self.r.workflow.main_head(),before)
        self.assertEqual((self.main/original['path']).read_text(),original['raw'])
        self.assertIn('Second edit',self.r.artifact(original['id'])['body'])
        self.assertEqual(len(self.r.proposals()),1)
        self.assertEqual(self.r.proposals()[0]['files'],[original['path']])
        resumed=Repository(self.main)
        self.assertEqual(resumed.workflow.active,identity)
        self.assertIn('First edit',resumed.artifact(original['id'])['body'])
        resumed.workflow.switch()
        self.assertEqual(resumed.artifact(original['id'])['raw'],original['raw'])
        resumed.workflow.switch(identity)
        self.assertIn('Second edit',resumed.artifact(original['id'])['body'])
        self.assertTrue(resumed.clean())

    def test_checks_required_invalidated_by_edits_and_merge_records_both_parents(self):
        before=self.r.head(); self.edit('Change'); identity=self.r.workflow.active
        with self.assertRaises(Problem): self.r.decide(identity,'approve')
        self.assertTrue(self.r.workflow.update(identity)['merge_ready'])
        self.edit('Later change')
        with self.assertRaises(Problem): self.r.decide(identity,'approve')
        checked=self.r.workflow.update(identity)
        self.r.decide(identity,'approve')
        self.assertIsNone(self.r.workflow.active)
        self.assertEqual(self.r.root,self.main)
        parents=self.r.git('rev-list','--parents','-n','1','HEAD').split()[1:]
        self.assertEqual(parents,[before,checked['commit']])
        self.assertIn('Later change',self.r.artifact('REQ-SAFE-001')['body'])
        self.assertTrue(self.r.clean())

    def test_new_main_invalidates_check_then_nonconflicting_update_retains_both(self):
        self.edit('Proposal edit'); identity=self.r.workflow.active
        self.r.workflow.update(identity)
        self.external_main('main-note.txt','A main update')
        with self.assertRaises(Problem): self.r.decide(identity,'approve')
        checked=self.r.workflow.update(identity)
        self.assertTrue(checked['merge_ready'])
        self.assertEqual((self.r.root/'main-note.txt').read_text(),'A main update')
        self.r.decide(identity,'approve')
        self.assertIn('Proposal edit',self.r.artifact('REQ-SAFE-001')['body'])

    def test_main_update_can_be_inspected_before_separate_checks_and_approval(self):
        self.edit('Proposal edit'); identity=self.r.workflow.active; before=self.r.head()
        self.external_main('main-note.txt','Approved change from main')
        main=self.r.workflow.main_head()
        with self.assertRaises(Problem): self.r.workflow.check_proposal(identity)
        self.assertEqual(self.r.head(),before, 'Checking must not silently update the branch')
        updated=self.r.workflow.update(identity,run_checks=False)
        self.assertEqual(self.r.workflow.main_head(),main)
        self.assertEqual((self.r.root/'main-note.txt').read_text(),'Approved change from main')
        self.assertIsNone(updated['checks'])
        self.assertFalse(updated['merge_ready'])
        self.assertEqual(updated['last_update']['files'],['main-note.txt'])
        self.assertIn('+Approved change from main',updated['last_update']['diff'])
        with self.assertRaises(Problem): self.r.decide(identity,'approve')
        self.edit('Adjustment after inspecting the combined result')
        self.assertTrue(self.r.workflow.check_proposal(identity)['merge_ready'])
        self.r.decide(identity,'approve')
        self.assertIn('Adjustment after inspecting',self.r.artifact('REQ-SAFE-001')['body'])

    def test_separate_update_conflict_resolution_still_needs_checks_after_restart(self):
        original=self.r.artifact('REQ-SAFE-001')
        self.edit('Proposal ending'); identity=self.r.workflow.active
        self.external_main(original['path'],original['raw']+'\nMain ending\n')
        main=self.r.workflow.main_head()
        self.assertTrue(self.r.workflow.update(identity,run_checks=False)['conflicts'])
        self.r=Repository(self.main)
        with self.assertRaises(Problem): self.r.workflow.check_proposal(identity)
        f=self.r.workflow.conflict(identity,original['path'])
        p=self.r.workflow.resolve(identity,original['path'],'manual',original['raw']+'\nCombined ending\n',f['commit'],f['main'])
        self.assertEqual(self.r.workflow.main_head(),main)
        self.assertIsNone(p['checks']); self.assertFalse(p['merge_ready'])
        self.assertIn('+Combined ending',p['last_update']['diff'])
        with self.assertRaises(Problem): self.r.decide(identity,'approve')
        self.assertTrue(self.r.workflow.check_proposal(identity)['merge_ready'])

    def test_repeated_update_on_current_main_needs_a_fresh_check_without_empty_commit(self):
        self.edit('Proposal edit'); identity=self.r.workflow.active
        self.r.workflow.check_proposal(identity)
        head=self.r.head()
        p=self.r.workflow.update(identity,run_checks=False)
        self.assertEqual(self.r.head(),head)
        self.assertEqual(p['last_update']['files'],[])
        self.assertIsNone(p['checks'])
        self.assertFalse(p['merge_ready'])
        self.assertTrue(self.r.workflow.check_proposal(identity)['merge_ready'])

    def test_conflicts_can_be_resolved_with_edited_text_and_rechecked(self):
        original=self.r.artifact('REQ-SAFE-001')
        self.edit('Proposal ending'); identity=self.r.workflow.active
        self.external_main(original['path'],original['raw']+'\nMain ending\n')
        updated=self.r.workflow.update(identity)
        self.assertEqual(updated['conflicts'],[original['path']])
        with self.assertRaises(Problem): self.r.decide(identity,'approve')
        conflict=self.r.workflow.conflict(identity,original['path'])
        self.assertIn('Proposal ending',conflict['ours'])
        self.assertIn('Main ending',conflict['main_content'])
        resolved=self.r.workflow.resolve(identity,original['path'],'manual',original['raw']+'\nBoth endings reconciled.\n',conflict['commit'],conflict['main'])
        self.assertTrue(resolved['merge_ready'])
        self.r.decide(identity,'approve')
        self.assertIn('Both endings reconciled',self.r.artifact(original['id'])['body'])

    def test_semantic_conflict_blocks_merge_even_when_git_merge_is_clean(self):
        raw=serialize({'ekf':'0.1','id':'DUP-001','type':'requirement','title':'Proposal concept'},'Meaning')
        self.r.save('engineering/proposal.md',raw)
        identity=self.r.workflow.active
        self.external_main('engineering/main.md',raw.replace('Proposal concept','Main concept'))
        checked=self.r.workflow.update(identity)
        self.assertEqual(checked['conflicts'],[])
        self.assertFalse(checked['merge_ready'])
        self.assertTrue(any(f['rule']=='duplicate-id' for f in checked['checks']['findings']))
        with self.assertRaises(Problem): self.r.decide(identity,'approve')

    def test_missing_attachment_blocks_merge_and_uploads_remain_isolated(self):
        a=self.edit('![Missing](assets/diagram.png)'); identity=self.r.workflow.active
        checked=self.r.workflow.update(identity)
        self.assertFalse(checked['checks']['passed'])
        self.r.save(a['path'],a['raw'],a['hash'],assets=[{'name':'diagram.png','content':base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()}])
        asset=Path(a['path']).parent/'assets/diagram.png'
        self.assertFalse((self.main/asset).exists())
        self.assertTrue(self.r.workflow.update(identity)['merge_ready'])
        self.r.decide(identity,'approve')
        self.assertTrue((self.main/asset).exists())

    def test_rejection_archives_and_does_not_modify_main(self):
        before=self.r.head(); self.edit('Rejected change'); identity=self.r.workflow.active
        branch=self.r.proposals()[0]['branch']; head=self.r.head()
        self.r.decide(identity,'reject')
        self.assertEqual(self.r.head(),before)
        self.assertEqual(self.r.git('rev-parse',branch).strip(),head)
        self.assertEqual(self.r.proposals()[0]['status'],'rejected')
        with self.assertRaises(Problem): self.r.workflow.switch(identity)

    def test_resource_changes_accumulate_and_context_guard_rejects_stale_tab(self):
        self.edit('Draft change'); identity=self.r.workflow.active
        self.r.workflow.save_files([{'path':'tools/new.py','content':'print(42)\n'}])
        self.assertEqual(len(self.r.proposals()),1)
        self.assertIn('tools/new.py',self.r.proposals()[0]['files'])
        self.assertFalse((self.main/'tools/new.py').exists())
        with self.assertRaises(Problem): self.r.workflow.assert_context('main')
        self.r.workflow.switch()
        with self.assertRaises(Problem): self.r.workflow.assert_context(identity)

    def test_main_ref_race_is_rejected_without_overwriting_new_main_files(self):
        self.edit('Draft change'); identity=self.r.workflow.active
        self.r.workflow.update(identity)
        git=self.r.git
        def racing_git(*args,**kwargs):
            result=git(*args,**kwargs)
            if args[0]=='commit-tree': self.external_main('racing.txt','Keep concurrent main content')
            return result
        with patch.object(self.r,'git',side_effect=racing_git),self.assertRaises(Problem):
            self.r.decide(identity,'approve')
        self.assertEqual((self.main/'racing.txt').read_text(),'Keep concurrent main content')
        self.assertEqual(self.r.git('status','--porcelain',cwd=self.main).strip(),'')
        self.assertNotIn('Draft change',(self.main/self.r.artifact('REQ-SAFE-001')['path']).read_text())

    def test_main_change_during_first_save_preserves_new_content(self):
        for generic in (False, True):
            with self.subTest(generic=generic):
                self.r.workflow.switch()
                original=self.r.artifact('REQ-SAFE-001')
                external=original['raw']+'\nExternal main edit\n'
                ensure=self.r.workflow.ensure_draft
                def race(title):
                    self.external_main(original['path'],external)
                    ensure(title)
                with patch.object(self.r.workflow,'ensure_draft',side_effect=race),self.assertRaises(Problem):
                    if generic:
                        self.r.workflow.save_files([{'path':original['path'],'content':original['raw']+'\nStale save\n'}])
                    else:
                        self.edit('Stale save')
                self.assertEqual((self.main/original['path']).read_text(),external)
                self.assertEqual(self.r.artifact(original['id'])['raw'],external)
                self.assertTrue(self.r.clean())

    def test_binary_conflict_preserves_selected_bytes(self):
        self.external_main('diagram.bin','original')
        self.r.workflow.save_files([{'path':'diagram.bin','content':'ours\x00bytes'}]); identity=self.r.workflow.active
        self.external_main('diagram.bin','main\x00bytes')
        self.r.workflow.update(identity)
        f=self.r.workflow.conflict(identity,'diagram.bin')
        self.assertTrue(f['binary'])
        p=self.r.workflow.resolve(identity,'diagram.bin','main',expected_commit=f['commit'],expected_main=f['main'])
        self.assertEqual((self.r.root/'diagram.bin').read_bytes(),b'main\x00bytes')
        self.assertTrue(p['checks']['passed'])

    def test_failed_main_checkout_aborts_prepared_ref_transaction(self):
        before=self.r.head(); self.edit('Draft change'); identity=self.r.workflow.active
        self.r.workflow.update(identity); git=self.r.git
        def fail_checkout(*args,**kwargs):
            if args[0]=='read-tree': raise Problem('Simulated checkout failure')
            return git(*args,**kwargs)
        with patch.object(self.r,'git',side_effect=fail_checkout),self.assertRaises(Problem):
            self.r.decide(identity,'approve')
        self.assertEqual(self.r.workflow.main_head(),before)
        self.assertEqual(self.r.git('status','--porcelain',cwd=self.main).strip(),'')
        self.assertTrue(self.r.workflow.update(identity)['merge_ready'])
        self.r.decide(identity,'approve')
