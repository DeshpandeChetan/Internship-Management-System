// Run with PLAYWRIGHT_MODULE pointing to an installed playwright package.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const handler = fs.readFileSync(path.join(__dirname, '../../templates/includes/form_handling.html'), 'utf8');

(async () => {
    const browser = await chromium.launch({ headless: true, executablePath: process.env.IMS_BROWSER_PATH || undefined });
    try {
        for (const modal of [true, false]) {
            const page = await browser.newPage();
            let requests = 0;
            let submitted = '';
            const html = `<html><body><div class="${modal ? 'modal show' : 'standalone'}">
                <form action="/save" method="post" enctype="multipart/form-data">
                <input name="first_name" value="Preserved Name" required>
                <input name="email" value="valid@example.com" type="email" required>
                <textarea name="remarks">Preserved remarks</textarea>
                <input type="file" name="document">
                <button type="submit" name="action" value="save">Save</button></form></div>
                <script>window.legacyCalls = 0; document.addEventListener('submit', () => window.legacyCalls++);</script>
                ${handler}</body></html>`;
            await page.route('http://ims.test/**', async route => {
                if (route.request().method() !== 'POST') return route.fulfill({ contentType: 'text/html', body: html });
                requests++;
                submitted = route.request().postData();
                if (requests === 3) return route.fulfill({status: 200, contentType: 'application/json',
                    body: JSON.stringify({success: true, redirect_url: '/done'})});
                await route.fulfill({status: 400, contentType: 'application/json', body: JSON.stringify({
                    success: false, errors: {email: ['Email already exists.'], __all__: ['<script>unsafe()</script>']}
                })});
            });
            await page.goto('http://ims.test/form');
            await page.locator('[name="document"]').setInputFiles({name: 'retained.txt', mimeType: 'text/plain', buffer: Buffer.from('retained file')});
            await page.getByRole('button', {name: 'Save'}).click();
            await page.locator('[name="email"].is-invalid').waitFor();
            assert.equal(await page.locator('[name="first_name"]').inputValue(), 'Preserved Name');
            assert.equal(await page.locator('[name="remarks"]').inputValue(), 'Preserved remarks');
            assert.equal(await page.locator('[name="document"]').evaluate(el => el.files[0].name), 'retained.txt');
            assert.equal(await page.evaluate(() => window.legacyCalls), 0);
            assert.equal(requests, 1);
            assert.ok(submitted.includes('name="action"'));
            assert.equal(await page.locator('.ims-form-errors script').count(), 0);
            if (modal) assert.equal(await page.locator('.modal.show').count(), 1);
            assert.equal(await page.locator('button').isEnabled(), true);
            await page.locator('[name="email"]').fill('');
            await page.getByRole('button', {name: 'Save'}).click();
            assert.equal(requests, 1);
            await page.locator('[name="email"]').fill('corrected@example.com');
            await page.getByRole('button', {name: 'Save'}).click();
            await page.waitForFunction(() => !document.querySelector('form').dataset.imsSubmitting);
            assert.equal(requests, 2);
            assert.ok(submitted.includes('corrected@example.com'));
            assert.equal(await page.locator('[name="document"]').evaluate(el => el.files.length), 1);
            await page.getByRole('button', {name: 'Save'}).click();
            await page.waitForURL('http://ims.test/done');
            assert.equal(requests, 3);
            await page.close();
        }
        console.log('Browser checks passed: modal/standalone errors, retained text/files, correction, submitter, one request, safe error text, success redirect.');
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
