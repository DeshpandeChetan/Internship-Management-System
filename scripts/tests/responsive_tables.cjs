const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '../..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const asset = (variable, fallback) => fs.readFileSync(process.env[variable] || path.join(process.env.TEMP, fallback), 'utf8');
const bootstrap = asset('IMS_BOOTSTRAP_CSS', 'ims-login-bootstrap.css');
const jquery = asset('IMS_JQUERY_JS', 'ims-table-jquery.js');
const datatables = asset('IMS_DATATABLES_JS', 'ims-table-datatables.js');
const bootstrapJS = asset('IMS_BOOTSTRAP_JS', 'ims-table-bootstrap.js');
const sharedCSS = read('static/css/responsive-tables.css');
const sharedJS = read('static/js/responsive-tables.js');
const baseCSS = read('templates/layout/base.html').match(/<style>([\s\S]*?)<\/style>/)[1];
const pages = ['admin/breaks.html', 'admin/users.html', 'student/internships.html',
    'mentor/students.html', 'evaluator/pending_assessments.html', 'hod/students.html',
    'hod/consolidated_report.html']; // Coordinator uses the HoD views/templates.

(async () => {
    const browser = await chromium.launch({ executablePath: process.env.IMS_BROWSER_PATH || undefined });
    try {
        for (const template of pages) {
            const source = read('templates/' + template);
            const header = source.match(/<thead[^>]*>([\s\S]*?)<\/thead>/)[1];
            const columns = (header.match(/<th\b/g) || []).length;
            const localCSS = Array.from(source.matchAll(/<style>([\s\S]*?)<\/style>/g), match => match[1]).join('\n');
            const tableID = source.match(/<table[^>]*id="([^"]+)"/)?.[1] || 'fixture';
            const rows = Array.from({ length: 18 }, (_, row) => '<tr>' + Array.from({ length: columns }, (_, col) =>
                col === columns - 1 ? '<td><div class="dropdown"><button class="btn dropdown-toggle" data-bs-toggle="dropdown">Actions</button><ul class="dropdown-menu dropdown-menu-end"><li><button class="dropdown-item" data-bs-toggle="modal" data-bs-target="#details">View details</button></li></ul></div></td>' :
                    `<td>${String(row).padStart(2, '0')} ${col === 1 ? 'verylongstudentemailaddresswithoutspaces@example.com' : 'Student internship information'}</td>`).join('') + '</tr>').join('');
            for (const width of [320, 390, 768, 1440]) {
                const page = await browser.newPage({ viewport: { width, height: 900 } });
                const errors = [];
                page.on('pageerror', error => errors.push(error.message));
                page.on('dialog', async dialog => { errors.push(dialog.message()); await dialog.dismiss(); });
                await page.setContent(`<style>${bootstrap}\n${baseCSS}\n${localCSS}\n${sharedCSS}\nbody{overflow-x:visible}</style>
                    <main class="main-content"><div class="card data-table-wrapper admin-breaks-table student-internships-card"><div class="card-body"><div class="table-responsive"><table id="${tableID}" class="table"><thead>${header}</thead><tbody>${rows}</tbody></table></div></div></div></main>
                    <div class="modal" id="details" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-body">Selected record details</div></div></div></div>`);
                await page.addScriptTag({ content: jquery });
                await page.addScriptTag({ content: bootstrapJS });
                await page.addScriptTag({ content: datatables });
                // Keep test selectors stable while exercising the template's ID-specific CSS.
                const originalLocator = page.locator.bind(page);
                page.locator = selector => originalLocator(selector.replaceAll('#fixture', '#' + tableID));
                await page.evaluate(id => { window.tableTestAPI = $('#' + id).DataTable({ pageLength: 5 }); }, tableID);
                await page.addScriptTag({ content: sharedJS });
                assert.deepEqual(errors, []);
                if (width < 768) {
                    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${template}: page overflow at ${width}`);
                    assert.equal(await page.locator('#fixture tbody tr:first-child td[data-ims-label]').count(), columns);
                    assert.equal(await page.locator('#fixture thead').isVisible(), false);
                    assert.equal(await page.locator('#fixture tbody tr:first-child .ims-primary-field').count(), 1);
                    await page.locator('.ims-table-sort select').selectOption('0:desc');
                    assert.equal(await page.evaluate(() => tableTestAPI.order()[0][1]), 'desc');
                } else {
                    assert.equal(await page.locator('#fixture').evaluate(el => getComputedStyle(el).display), 'table');
                    if (width === 1440) {
                        await page.locator('.main-content').evaluate(el => { el.style.width = '500px'; });
                        await page.waitForFunction(() => document.querySelector('table').classList.contains('ims-card-layout'));
                        await page.locator('.main-content').evaluate(el => { el.style.width = ''; });
                        await page.waitForFunction(() => !document.querySelector('table').classList.contains('ims-card-layout'));
                    }
                }
                await page.evaluate(() => tableTestAPI.search('verylongstudentemail').draw());
                assert.equal(await page.evaluate(() => tableTestAPI.page.info().recordsDisplay), 18);
                await page.evaluate(() => tableTestAPI.order([0, 'desc']).draw());
                assert.ok((await page.locator('#fixture tbody tr:first-child td:first-child').textContent()).startsWith('17'));
                await page.evaluate(() => tableTestAPI.page('next').draw('page'));
                assert.equal(await page.evaluate(() => tableTestAPI.page()), 1);
                if (width < 768) {
                    await page.locator('#fixture .dropdown-toggle').first().click();
                    const bounds = await page.locator('#fixture .dropdown-menu.show').boundingBox();
                    assert.ok(bounds.x >= 0 && bounds.x + bounds.width <= width + 1, `${template}: dropdown overflow`);
                    await page.locator('#fixture .dropdown-menu.show button').click();
                    await page.locator('#details.show').waitFor();
                    await page.evaluate(() => bootstrap.Modal.getInstance(document.querySelector('#details')).hide());
                }
                if (process.env.IMS_SCREENSHOT_DIR && width < 768) await page.screenshot({ path: path.join(process.env.IMS_SCREENSHOT_DIR, template.replaceAll('/', '-') + '-' + width + '.png'), fullPage: true });
                await page.evaluate(() => tableTestAPI.search('no matching entry').draw());
                assert.ok((await page.locator('#fixture tbody').textContent()).includes('No matching'));
                await page.evaluate(() => tableTestAPI.clear().search('').draw());
                assert.ok((await page.locator('#fixture tbody').textContent()).includes('No data'));
                assert.deepEqual(errors, []);
                await page.close();
            }
            console.log('Passed mobile/tablet/desktop table checks:', template);
        }
    } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
