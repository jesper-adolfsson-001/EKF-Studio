/* Runs inside the existing isolated browser test repository. */
const { expect } = require(process.env.EKF_PLAYWRIGHT || '@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

module.exports = async function checkBaselines({page,context,base,repo}) {
  const original = await (await context.request.get(base+'/api/snapshot')).json();
  const baseline = page.locator('.baseline-entry').filter({hasText:'example-v0.1'});
  await baseline.getByRole('button',{name:'Browse',exact:true}).click();
  await expect(page.locator('.baseline-banner')).toContainText('example-v0.1');
  await expect(page.locator('.baseline-banner')).toContainText('Read only');
  await expect(page.getByRole('button',{name:'New artifact',exact:true})).toHaveCount(0);
  await expect(page.locator('.nav-item[data-page="changes"]')).toHaveCount(0);
  await page.locator('.graph-node[data-artifact="REQ-SAFE-001"]').click();
  await expect(page.locator('.drawer')).toBeVisible();
  await expect(page.getByRole('button',{name:'Close artifact',exact:true})).toBeFocused();
  await expect(page.getByRole('button',{name:'Edit artifact',exact:true}).first()).toBeHidden();
  await expect(page.getByRole('button',{name:'Record human review'})).toHaveCount(0);
  await page.getByRole('button',{name:'Markdown source',exact:true}).click();
  await expect(page.locator('.drawer pre')).toContainText('REQ-SAFE-001');
  await page.getByRole('button',{name:'Impact & context',exact:true}).click();
  await expect(page.locator('.drawer')).toContainText('Potentially affected neighborhood');
  await page.mouse.click(15,150);
  await expect(page.locator('.drawer')).toHaveCount(0);

  await page.locator('.nav-item[data-page="knowledge"]').click();
  await page.locator('#library-search').fill('Motor shaft');
  await expect(page.locator('tbody tr')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'New artifact',exact:true})).toHaveCount(0);
  await page.reload();
  await expect(page.locator('.baseline-banner')).toContainText('example-v0.1');
  await expect(page.locator('tbody tr')).toHaveCount(23);
  await page.locator('.nav-item[data-page="traceability"]').click();
  await expect(page.locator('.engineering-graph')).toBeVisible();
  await page.getByRole('button',{name:'Matrix',exact:true}).click();
  await expect(page.locator('tbody tr')).toHaveCount(5);
  await page.locator('.nav-item[data-page="verification"]').click();
  await expect(page.locator('tbody tr')).toHaveCount(5);

  await page.locator('.nav-item[data-page="reports"]').click();
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('button',{name:/Requirements specification/}).click();
  const download=await downloadPromise;
  const report=fs.readFileSync(await download.path(),'utf8');
  assert.ok(!report.includes('REQ-MECH-099'));
  const historical=await (await context.request.get(base+'/api/snapshot?ref=example-v0.1')).json();
  assert.ok(report.includes(historical.head));
  assert.equal((await context.request.post(base+'/api/baselines?ref='+historical.head,{data:{name:'must-not-exist'}})).status(),409);
  assert.equal((await (await context.request.get(base+'/api/snapshot')).json()).head,original.head);

  await page.getByRole('button',{name:'Return to current workspace',exact:true}).click();
  await expect(page.locator('.baseline-banner')).toHaveCount(0);
  await page.locator('.nav-item[data-page="knowledge"]').click();
  await page.locator('#library-search').fill('Motor shaft');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await expect(page.getByRole('button',{name:'New artifact',exact:true})).toBeVisible();

  await page.locator('.nav-item[data-page="activity"]').click();
  await page.locator('.baseline-entry').filter({hasText:'example-v0.1'}).getByRole('button',{name:'Compare',exact:true}).click();
  await expect(page.locator('.comparison-context')).toContainText('example-v0.1');
  await page.getByLabel('Compare to',{exact:true}).selectOption('browser-verified');
  await page.getByRole('button',{name:'Compare versions',exact:true}).last().click();
  await expect(page.locator('.comparison-context')).toContainText('browser-verified');
  const artifactRow=page.locator('tr').filter({hasText:'REQ-MECH-099'}).filter({has:page.getByRole('button',{name:'View changes',exact:true})});
  await expect(artifactRow).toContainText('added');
  await artifactRow.getByRole('button',{name:'View changes',exact:true}).click();
  await expect(page.locator('.modal')).toContainText('Motor shaft dimensional tolerance');
  await expect(page.locator('.modal pre').first()).toContainText('+id: REQ-MECH-099');
  await page.locator('.comparison-source-toggle').click();
  await expect(page.locator('.comparison-sources')).toContainText('Artifact does not exist in this version.');
  await page.keyboard.press('Escape');
  const resourceRow=page.locator('tr').filter({hasText:'tools/margin.py'});
  await resourceRow.getByRole('button',{name:'View changes',exact:true}).click();
  await expect(page.locator('.modal pre')).toContainText('+print(250 - 191)');
  await page.keyboard.press('Escape');
  await page.screenshot({path:'/tmp/ekf-baseline-comparison.png',fullPage:true,animations:'disabled'});

  await page.getByRole('button',{name:'Swap',exact:true}).click();
  await expect(page.locator('.comparison-context')).toContainText('browser-verified');
  await expect(artifactRow).toContainText('removed');
  await page.getByLabel('Compare from',{exact:true}).selectOption('browser-verified');
  await page.getByLabel('Compare to',{exact:true}).selectOption('browser-verified');
  await page.getByRole('button',{name:'Compare versions',exact:true}).last().click();
  await expect(page.getByRole('heading',{name:'No artifact changes',exact:true})).toBeVisible();
  await page.getByLabel('Compare to',{exact:true}).selectOption('');
  const notes=path.join(repo,'comparison-notes.txt');
  fs.writeFileSync(notes,'Uncommitted engineering note.\n');
  try {
    await page.getByRole('button',{name:'Compare versions',exact:true}).last().click();
    await expect(page.locator('.comparison-context')).toContainText('includes uncommitted files');
    await expect(page.locator('tr').filter({hasText:'comparison-notes.txt'})).toContainText('added');
  } finally {fs.unlinkSync(notes);}

  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.locator('body').evaluate(el=>el.scrollWidth>innerWidth),false,'Mobile comparison overflow');
  await page.getByLabel('Workspace version',{exact:true}).selectOption('example-v0.1');
  await expect(page.locator('.baseline-banner')).toBeVisible();
  assert.equal(await page.locator('body').evaluate(el=>el.scrollWidth>innerWidth),false,'Mobile baseline overflow');
  await page.screenshot({path:'/tmp/ekf-baseline-mobile.png',fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'Return to current workspace',exact:true}).click();
  await page.setViewportSize({width:1440,height:1100});
  console.log('Historical browsing, read-only UI, reports, comparisons, resource diffs, dirty files and mobile layout passed.');
};
