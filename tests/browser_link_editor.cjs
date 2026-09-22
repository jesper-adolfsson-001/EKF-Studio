const {expect}=require(process.env.EKF_PLAYWRIGHT||'@playwright/test');
const {spawnSync}=require('node:child_process');
const assert=require('node:assert/strict');

module.exports=async({page,context,base,repo})=>{
  const snapshot=async()=> (await context.request.get(base+'/api/snapshot')).json();
  const artifact=async id=> (await context.request.get(base+'/api/artifact?id='+encodeURIComponent(id))).json();
  const head=async()=> (await snapshot()).head;
  const apiPost=async(path,data)=>{const r=await context.request.post(base+'/api/'+path,{data});assert.equal(r.status(),200,await r.text());return r.json();};
  const linkButton=action=>page.locator(`[data-link-action="${action}"]`);
  // A real repository large enough to require several picker pages.
  const seed=spawnSync('python3',['-c',`import json,sys
from ekf.core import Repository,serialize
repo=Repository(sys.argv[1])
repo.save_many([{'path': 'engineering/link-tests/'+a['id']+'.md', 'raw':serialize(a,'Picker pagination fixture.')} for a in json.load(sys.stdin)])`,repo],{
    input:JSON.stringify(Array.from({length:65},(_,i)=>({ekf:'0.1',id:'LINK-'+String(i).padStart(3,'0'),type:'link-test',title:'Link test item '+i,discipline:'Integration',custom:{keep:true},relations:i===0?[{type:'implemented-by',resource:'tools/analyze_shutdown.py',custom:'preserve'}]:[]}))),encoding:'utf8'});
  assert.equal(seed.status,0,seed.stderr);
  await page.goto(base+'/#knowledge');
  await page.reload();
  await page.getByRole('button',{name:'New artifact',exact:true}).click();
  await page.locator('#edit-id').fill('LINK-NEW');
  await page.locator('#edit-title').fill('A draft with incoming links');
  await page.locator('#edit-body').fill('Keep my unsaved engineering meaning.');
  await page.locator('[data-action="editor-links"][data-direction="incoming"]').click();
  await expect(page.locator('#link-direction')).toHaveValue('incoming');
  await page.locator('#link-item-type').selectOption('link-test');
  await page.locator('#link-discipline').selectOption('Integration');
  await expect(page.locator('[data-link-select]')).toHaveCount(20);
  await page.locator('[data-link-select="LINK-000"]').check();
  await page.locator('#link-pagination').getByRole('button',{name:'Next',exact:true}).click();
  await page.locator('[data-link-select="LINK-020"]').check();
  await page.locator('#link-query').fill('LINK-064');
  await page.locator('[data-link-select="LINK-064"]').focus();
  await page.keyboard.press('Space');
  await expect(page.locator('#link-selected')).toContainText('3 selected');
  await page.locator('#link-item-type').selectOption('requirement');
  await expect(page.locator('#link-results')).toContainText('No matching items');
  await expect(page.locator('#link-selected')).toContainText('LINK-000');
  await page.locator('#link-type').fill('custom-supports');
  await linkButton('stage').click();
  await expect(page.locator('#link-review-title')).toContainText('3 pending link changes');
  await expect(page.locator('#link-review-list')).toContainText('LINK-NEW');
  const beforeCreate=await head();
  await page.screenshot({path:'/tmp/ekf-link-picker.png',fullPage:true,animations:'disabled'});
  await linkButton('save').click();
  await expect(page.locator('#edit-body')).toHaveValue('Keep my unsaved engineering meaning.');
  await expect(page.locator('#editor-links-summary')).toContainText('3 source items');
  assert.equal(await head(),beforeCreate,'Applying to draft must not commit');
  // Cancelling a second picker preserves previously applied draft links and all form fields.
  await page.locator('[data-action="editor-links"][data-direction="outgoing"]').click();
  await page.locator('#link-query').fill('LINK-001');
  await page.locator('[data-link-select="LINK-001"]').check();
  await linkButton('stage').click();
  await page.keyboard.press('Escape');
  await expect(page.locator('#edit-body')).toHaveValue('Keep my unsaved engineering meaning.');
  await expect(page.locator('#editor-links-summary')).toContainText('0 outgoing links');
  await page.locator('[data-action="editor-links"][data-direction="outgoing"]').click();
  await expect(page.locator('#link-query')).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Save artifact',exact:true}).click();
  await expect(page.locator('.drawer h2')).toHaveText('A draft with incoming links');
  const created=await artifact('LINK-NEW');
  assert.ok(created.body.includes('Keep my unsaved'));
  for(const id of ['LINK-000','LINK-020','LINK-064'])assert.ok((await artifact(id)).meta.relations.some(r=>r.type==='custom-supports'&&r.target==='LINK-NEW'));
  const commits=spawnSync('git',['-C',repo,'rev-list','--count',beforeCreate+'..HEAD'],{encoding:'utf8'});
  assert.equal(commits.stdout.trim(),'1');

  // Pane entry points; add both directions in one transaction and skip duplicates.
  await page.getByRole('button',{name:'Add outgoing links',exact:true}).click();
  await page.locator('#link-query').fill('LINK-001');
  await page.locator('[data-link-select="LINK-001"]').check();
  await linkButton('stage').click();
  await expect(page.locator('[data-link-select="LINK-001"]')).toBeDisabled();
  await page.locator('#link-direction').selectOption('incoming');
  await page.locator('#link-query').fill('LINK-002');
  await page.locator('[data-link-select="LINK-002"]').check();
  await linkButton('stage').click();
  await linkButton('save').click();
  await expect(page.locator('.drawer')).toBeVisible();
  assert.ok((await artifact('LINK-NEW')).meta.relations.some(r=>r.target==='LINK-001'));
  assert.ok((await artifact('LINK-002')).meta.relations.some(r=>r.target==='LINK-NEW'));

  // Search, retype and remove incoming links from the source without deleting any item.
  await page.getByRole('button',{name:'Manage links',exact:true}).click();
  await page.locator('#link-manage-query').fill('LINK-020');
  await page.locator('[data-link-retype]').fill('validated-by');
  await page.locator('#link-manage-query').click();
  await page.locator('#link-manage-query').fill('LINK-064');
  await linkButton('remove').click();
  await expect(page.locator('#link-review-title')).toContainText('3 pending link changes');
  await linkButton('save').click();
  await expect(page.locator('.drawer')).toBeVisible();
  assert.ok((await artifact('LINK-020')).meta.relations.some(r=>r.type==='validated-by'&&r.target==='LINK-NEW'));
  assert.ok(!(await artifact('LINK-064')).meta.relations.some(r=>r.target==='LINK-NEW'));
  assert.equal((await artifact('LINK-064')).id,'LINK-064');

  // A concurrent source edit rejects the whole batch and keeps the user's pending choices.
  await page.getByRole('button',{name:'Add incoming links',exact:true}).click();
  await page.locator('#link-query').fill('LINK-003');
  await page.locator('[data-link-select="LINK-003"]').check();
  await linkButton('stage').click();
  await page.locator('#link-query').fill('LINK-004');
  await page.locator('[data-link-select="LINK-004"]').check();
  await linkButton('stage').click();
  const concurrent=await artifact('LINK-003');
  await apiPost('artifact',{path:concurrent.path,raw:concurrent.raw+'\nChanged elsewhere.\n',expected_hash:concurrent.hash});
  const beforeConflict=await head();
  await linkButton('save').click();
  await expect(page.locator('#form-error')).toContainText('LINK-003 changed');
  await expect(page.locator('#link-review-title')).toContainText('2 pending link changes');
  assert.equal(await head(),beforeConflict);
  assert.equal((await artifact('LINK-004')).meta.relations.length,0);
  await linkButton('cancel').click();
  await page.keyboard.press('Escape');

  // Retyping a resource preserves its custom metadata; mobile modal stays within the viewport.
  await page.locator('#library-search').fill('LINK-000');
  await page.locator('tr[data-artifact="LINK-000"]').click();
  await page.getByRole('button',{name:'Manage links',exact:true}).click();
  await page.locator('#link-manage-query').fill('analyze_shutdown.py');
  await page.locator('[data-link-retype]').fill('custom-method');
  await page.locator('#link-manage-query').click();
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'/tmp/ekf-link-manager-mobile.png',fullPage:true,animations:'disabled'});
  assert.equal(await page.locator('.modal').evaluate(el=>el.scrollWidth>el.clientWidth),false,'Link dialog overflow');
  await linkButton('save').click();
  await expect(page.locator('.drawer')).toBeVisible();
  const resource=(await artifact('LINK-000')).meta.relations.find(r=>r.resource);
  assert.deepEqual(resource,{type:'custom-method',resource:'tools/analyze_shutdown.py',custom:'preserve'});
  await page.keyboard.press('Escape');
  await page.setViewportSize({width:1440,height:1100});

  await page.locator('#workspace-revision').selectOption('browser-verified');
  await page.locator('#library-search').fill('REQ-SAFE-001');
  await page.locator('tr[data-artifact="REQ-SAFE-001"]').click();
  await expect(page.getByRole('button',{name:'Manage links',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Add incoming links',exact:true})).toHaveCount(0);
  const readonlyResponse=await context.request.post(base+'/api/links?ref=browser-verified',{data:{updates:[]}});
  assert.equal(readonlyResponse.status(),409);
  await page.keyboard.press('Escape');
  await page.locator('#workspace-revision').selectOption('');
  await expect(page.locator('.baseline-banner')).toHaveCount(0);
  console.log('Link picker pagination, both directions, drafts, custom/resource links, atomic conflicts, mobile and read-only baselines passed.');
};
