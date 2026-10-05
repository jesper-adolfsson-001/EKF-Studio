const {expect}=require(process.env.EKF_PLAYWRIGHT||'@playwright/test');
const {spawnSync}=require('node:child_process');
const assert=require('node:assert/strict');

module.exports=async({page,context,base,repo})=>{
  const get=async path=>(await context.request.get(base+'/api/'+path)).json();
  const head=async()=>(await get('snapshot')).head;
  const parentId='REQ-SAFE-001';
  const parent=await get('artifact?id='+parentId);
  const menu=page.getByRole('menu',{name:'Actions for '+parentId});
  const node=()=>page.locator(`.graph-node[data-artifact="${parentId}"]`);
  const create=page.getByRole('button',{name:'Create child',exact:true});
  await page.locator('.nav-item[data-page="overview"]').click();
  await page.locator('#overview-root-type').selectOption('');
  await page.locator('#overview-root').selectOption(parentId);
  const original=await head();

  await node().click({button:'right'});
  await expect(menu).toBeVisible();
  await expect(page.locator('.drawer')).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(menu).toHaveCount(0);
  try {await expect(node()).toBeFocused();}
  catch(error){console.log('Graph focus diagnostic',await node().evaluate(n=>({same:document.activeElement===n,hasFocus:document.hasFocus(),active:document.activeElement?.outerHTML,matches:n.matches(':focus')})));throw error;}
  await page.keyboard.press('Shift+F10');
  await expect(menu).toBeVisible();
  await page.keyboard.press('ArrowDown');
  await expect(menu.getByRole('menuitem',{name:'Open item',exact:true})).toBeFocused();
  await page.keyboard.press('ArrowUp');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog',{name:'Create child artifact',exact:true})).toBeVisible();
  await expect(page.locator('#child-relationship')).toHaveValue('derives-from');
  await expect(page.locator('#edit-type')).toHaveValue(parent.type);
  await page.getByRole('button',{name:'Cancel',exact:true}).click();
  assert.equal(await head(),original,'Opening/cancelling child creation must not write');

  await node().click({button:'right'});
  await menu.getByRole('menuitem',{name:'Create child…',exact:true}).click();
  await page.locator('#edit-id').fill('GRAPH-CHILD-001');
  await page.locator('#edit-title').fill('Refined shutdown requirement');
  await page.getByRole('button',{name:'Markdown source',exact:true}).click();
  await page.locator('#edit-body').fill('A new requirement created from the overview graph.');
  await page.locator('#child-relationship').fill('');
  await create.click();
  await expect(page.locator('#form-error')).toContainText('Choose a relationship type');
  await page.locator('#child-relationship').fill('refines');
  await expect(page.locator('#child-link-preview')).toHaveText('GRAPH-CHILD-001 → refines → REQ-SAFE-001');
  await page.screenshot({path:'/tmp/ekf-create-graph-child.png',animations:'disabled'});
  await create.click();
  await expect(page.locator('.drawer-head h2')).toHaveText('Refined shutdown requirement');
  const first=await get('artifact?id=GRAPH-CHILD-001');
  assert.ok(first.meta.relations.some(r=>r.type==='refines'&&r.target===parentId));
  assert.equal((await get('artifact?id='+parentId)).hash,parent.hash,'Child → parent must preserve parent file');
  await page.keyboard.press('Escape');

  await page.locator('.nav-item[data-page="traceability"]').click();
  await page.locator('#graph-focus').selectOption(parentId);
  await expect(page.locator('.graph-edge[data-source="GRAPH-CHILD-001"][data-target="REQ-SAFE-001"]')).toHaveCount(1);
  await node().click({button:'right'});
  await menu.getByRole('menuitem',{name:'Create child…',exact:true}).click();
  await page.locator('#edit-id').fill('GRAPH-CHILD-002');
  await page.locator('#edit-title').fill('Shutdown verification child');
  await page.locator('#edit-type').selectOption('verification');
  await page.locator('#child-relationship').fill('verified-by');
  await page.locator('#child-link-direction').selectOption('parent-child');
  await expect(page.locator('#child-link-preview')).toHaveText('REQ-SAFE-001 → verified-by → GRAPH-CHILD-002');
  // A nested link picker must preserve the parent relationship and all unsaved fields.
  await page.locator('[data-action="editor-links"][data-direction="incoming"]').click();
  await page.keyboard.press('Escape');
  await expect(page.locator('#child-relationship')).toHaveValue('verified-by');
  const before=await head();
  await create.click();
  await expect(page.locator('.drawer-head h2')).toHaveText('Shutdown verification child');
  assert.equal((await get('artifact?id=GRAPH-CHILD-002')).type,'verification');
  const linkedParent=await get('artifact?id='+parentId);
  assert.deepEqual(linkedParent.meta.relations,[...parent.meta.relations,{type:'verified-by',target:'GRAPH-CHILD-002'}]);
  assert.equal(spawnSync('git',['-C',repo,'rev-list','--count',before+'..HEAD'],{encoding:'utf8'}).stdout.trim(),'1');
  await page.keyboard.press('Escape');
  await expect(page.locator('.graph-edge[data-source="REQ-SAFE-001"][data-target="GRAPH-CHILD-002"]')).toHaveCount(1);

  // Stale parent blocks creation as well as the link; the draft stays available.
  await node().click({button:'right'});
  await menu.getByRole('menuitem',{name:'Create child…',exact:true}).click();
  await page.locator('#edit-id').fill('GRAPH-CONFLICT');
  await page.locator('#edit-title').fill('Keep this draft after a conflict');
  await page.locator('#child-link-direction').selectOption('parent-child');
  await page.locator('#child-relationship').fill('custom-child-link');
  const changed=await context.request.post(base+'/api/artifact',{data:{path:linkedParent.path,raw:linkedParent.raw+'\nConcurrent clarification.\n',expected_hash:linkedParent.hash}});
  assert.equal(changed.status(),200);
  const afterConcurrent=await head();
  await create.click();
  await expect(page.locator('#form-error')).toContainText('REQ-SAFE-001 changed');
  await expect(page.locator('#edit-title')).toHaveValue('Keep this draft after a conflict');
  assert.equal(await head(),afterConcurrent);
  assert.ok(!(await get('snapshot')).artifacts.some(a=>a.id==='GRAPH-CONFLICT'));
  await page.keyboard.press('Escape');

  // Baseline menu supports inspection but cannot create children.
  await page.locator('#workspace-revision').selectOption('browser-verified');
  await expect(page.locator('.baseline-banner')).toContainText('browser-verified');
  await node().click({button:'right'});
  await expect(menu).toContainText('Baseline · read only');
  await expect(menu.getByRole('menuitem',{name:'Create child…',exact:true})).toHaveCount(0);
  await menu.getByRole('menuitem',{name:'Open item',exact:true}).click();
  await expect(page.locator('.drawer')).toContainText('Baseline browser-verified');
  await page.keyboard.press('Escape');
  await page.locator('#workspace-revision').selectOption('');
  await expect(page.locator('.baseline-banner')).toHaveCount(0);
  await page.locator('#graph-focus').selectOption(parentId);
  // Clamp the menu to the viewport, and dismiss it on an outside click.
  await node().evaluate(el=>el.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:1438,clientY:1098})));
  const bounds=await menu.boundingBox();
  assert.ok(bounds.x+bounds.width<=1440&&bounds.y+bounds.height<=1100);
  await page.locator('h1').click();
  await expect(menu).toHaveCount(0);
  await node().click();
  await expect(page.locator('.drawer-head h2')).toHaveText(parent.title);
  await page.keyboard.press('Escape');
  console.log('Graph child creation: both graphs, relationship/direction selection, one-commit saves, cancellation, conflict protection, keyboard menu and baselines passed.');
};
