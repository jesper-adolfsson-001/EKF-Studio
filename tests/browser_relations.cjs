const { expect } = require(process.env.EKF_PLAYWRIGHT || '@playwright/test');
const assert = require('node:assert/strict');

module.exports = async function checkRelations({page,context,base}) {
  const snapshot=await (await context.request.get(base+'/api/snapshot')).json();
  const title=id=>snapshot.artifacts.find(a=>a.id===id).title;
  const openLink=async(container,direction,id)=>{
    const group=container.locator(`.relation-group.${direction}`),link=group.locator(`button[data-artifact="${id}"]`);
    if(!await link.isVisible())await group.locator('summary').click();
    await link.click();
    await expect(page.locator('.drawer-head h2')).toHaveText(title(id));
  };
  await page.locator('.nav-item[data-page="knowledge"]').click();
  await page.locator('#library-search').fill('VER-SAFE-001');
  let row=page.locator('tr[data-artifact="VER-SAFE-001"]');
  const incoming=snapshot.edges.filter(e=>e.target==='VER-SAFE-001').length;
  const outgoing=snapshot.artifacts.find(a=>a.id==='VER-SAFE-001').meta.relations.length;
  await expect(row.locator('.incoming .relation-direction b')).toHaveText(String(incoming));
  await expect(row.locator('.outgoing .relation-direction b')).toHaveText(String(outgoing));
  await openLink(row,'incoming','REQ-SAFE-001');
  await expect(page.locator('.drawer .detail-relations')).toBeVisible();
  await openLink(page.locator('.drawer .detail-relations'),'outgoing','VER-SAFE-001');
  await page.getByRole('button',{name:'Markdown source',exact:true}).click();
  await expect(page.locator('.drawer pre')).toBeVisible();
  await openLink(page.locator('.drawer .detail-relations'),'incoming','REQ-SAFE-001');
  await page.getByRole('button',{name:'Close artifact',exact:true}).click();
  await expect(page.locator('#library-search')).toHaveValue('VER-SAFE-001');

  await page.locator('#library-search').fill('REQ-SAFE-001');
  row=page.locator('tr[data-artifact="REQ-SAFE-001"]');
  await expect(row.locator('.outgoing .relation-chip:visible')).toHaveCount(2);
  await row.locator('.outgoing summary').click();
  await expect(page.locator('.drawer')).toHaveCount(0);
  await expect(row.locator('.outgoing .relation-chip:visible')).toHaveCount(5);
  await row.locator('.outgoing button[data-artifact="VER-SAFE-001"]').focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.drawer-head h2')).toHaveText(title('VER-SAFE-001'));
  await page.getByRole('button',{name:'Close artifact',exact:true}).click();
  await page.locator('#library-search').fill('');
  await page.screenshot({path:'/tmp/ekf-library-relations.png',fullPage:true,animations:'disabled'});

  await page.locator('#library-search').fill('VER-SAFE-001');
  row=page.locator('tr[data-artifact="VER-SAFE-001"]');
  await row.locator('button[data-action="resource"]').click();
  await expect(page.locator('.modal')).toContainText('tools/analyze_shutdown.py');
  await expect(page.locator('.drawer')).toHaveCount(0);
  await page.keyboard.press('Escape');

  await page.locator('#library-search').fill('REQ-SAFE-001');
  await page.getByRole('button',{name:'Card view',exact:true}).click();
  await expect(page.locator('.artifact-card-main')).toHaveCount(1);
  assert.equal(await page.locator('button button').count(),0,'Cards must not nest relation buttons inside another button');
  await openLink(page.locator('.artifact-card'),'outgoing','VER-SAFE-001');
  await page.getByRole('button',{name:'Close artifact',exact:true}).click();

  await page.setViewportSize({width:390,height:844});
  await openLink(page.locator('.artifact-card'),'outgoing','VER-SAFE-001');
  await expect(page.locator('.drawer .detail-relations')).toBeVisible();
  assert.equal(await page.locator('.drawer').evaluate(el=>el.scrollWidth>el.clientWidth),false,'Relation links overflow the mobile item pane');
  await page.screenshot({path:'/tmp/ekf-item-relations-mobile.png',fullPage:true,animations:'disabled'});
  await openLink(page.locator('.drawer .detail-relations'),'incoming','REQ-SAFE-001');
  await page.getByRole('button',{name:'Close artifact',exact:true}).click();
  assert.equal(await page.locator('body').evaluate(el=>el.scrollWidth>innerWidth),false,'Relation cards overflow the mobile page');
  await page.setViewportSize({width:1440,height:1100});
  await page.getByRole('button',{name:'Table view',exact:true}).click();

  await page.getByLabel('Workspace version',{exact:true}).selectOption('example-v0.1');
  await page.locator('#library-search').fill('VER-SAFE-001');
  row=page.locator('tr[data-artifact="VER-SAFE-001"]');
  await expect(row.locator('.outgoing .relation-direction b')).toHaveText('2');
  await openLink(row,'outgoing','EVID-SAFE-042');
  await expect(page.locator('.drawer')).toContainText('Read only');
  await openLink(page.locator('.drawer .detail-relations'),'incoming','VER-SAFE-001');
  await page.getByRole('button',{name:'Close artifact',exact:true}).click();
  await page.getByRole('button',{name:'Return to current workspace',exact:true}).click();
  await expect(page.locator('.baseline-banner')).toHaveCount(0);
  await page.locator('#library-search').fill('REQ-MECH-099');
  await expect(page.locator('.relations-cell .relation-direction b')).toHaveText(['0','0']);
  await page.locator('.artifact-title').click();
  await expect(page.locator('.drawer .relation-direction b')).toHaveText(['0','0']);
  await page.getByRole('button',{name:'Close artifact',exact:true}).click();
  await page.locator('.nav-item[data-page="activity"]').click();
  assert.equal((await (await context.request.get(base+'/api/snapshot')).json()).head,snapshot.head);
  console.log('Compact incoming/outgoing links, table/card navigation, pane traversal, keyboard, resources, baselines and mobile layout passed.');
};
