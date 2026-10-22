const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const read = name => fs.readFileSync(path.join(__dirname, '../../templates/', name), 'utf8');
const notifications = read('includes/notifications_script.html');
const students = read('admin/students.html');
const studentFunction = students.slice(students.indexOf('function viewStudent(id) {'), students.indexOf('function viewInternships(id) {'));

(async () => {
    const browser = await chromium.launch({headless: true, executablePath: process.env.IMS_BROWSER_PATH || undefined});
    try {
        const page = await browser.newPage();
        await page.route('http://ims.test/**', async route => {
            if (route.request().url().endsWith('/fail/')) return route.fulfill({status: 500, body: 'Error'});
            const data = route.request().url().includes('/students/') ? {
                name: 'Selected Student', email: 'selected@example.com',
                current_mentor: 'Current Mentor', internship_progress: {regular_completed: 3, regular_required: 8},
                internships: [{id: 'internship-1', number: '1', verification: 'Verified'}],
            } : {name: '<img src=x onerror=alert(1)>', email: 'selected-user@example.com', role: 'HoD/Coordinator'};
            return route.fulfill({contentType: 'application/json', body: JSON.stringify(data)});
        });
        await page.goto('http://ims.test/');
        await page.setContent(`<div id="imsMessages"></div>
            <div id="viewModal"><h5 class="modal-title"></h5><div id="viewModalBody"></div></div>
            <script>
            window.bootstrap = {
                Modal: {getOrCreateInstance: el => ({show: () => el.classList.add('show')})},
                Toast: {getOrCreateInstance: el => ({show: () => el.classList.add('show')})}
            };
            window.viewStudentInternship = id => window.selectedInternship = id;
            ${studentFunction}
            </script>${notifications}`);
        await page.evaluate(() => viewStudent('student-1'));
        await page.getByText('Selected Student', {exact: true}).waitFor();
        assert.ok(await page.locator('#viewModal').evaluate(el => el.classList.contains('show')));
        assert.ok((await page.locator('#viewModalBody').textContent()).includes('selected@example.com'));
        await page.getByRole('button', {name: '1', exact: true}).click();
        assert.equal(await page.evaluate(() => window.selectedInternship), 'internship-1');
        await page.evaluate(() => IMSDetails.open('User Details', '/users/1/'));
        await page.getByText('selected-user@example.com', {exact: true}).waitFor();
        assert.equal(await page.locator('#viewModalBody img').count(), 0);
        assert.ok(!(await page.locator('#viewModalBody').textContent()).includes('Selected Student'));
        await page.evaluate(() => IMSDetails.open('Student Details', '/fail/'));
        await page.locator('.alert.show').waitFor();
        assert.ok((await page.locator('#viewModalBody').textContent()).includes('Unable to load details'));
        console.log('Admin detail browser checks passed: selected record, internship link, safe rendering, loading failure toast.');
    } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode = 1;});
