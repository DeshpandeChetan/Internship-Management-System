(function () {
    'use strict';

    function prepareTables() {
        document.querySelectorAll('table').forEach(function (table) {
            let container = table.closest('.table-responsive, .ims-table-container');
            if (!container) {
                container = document.createElement('div');
                container.className = 'ims-table-container';
                table.before(container);
                container.appendChild(table);
            }
            container.classList.add('ims-table-container');
            if (!table.tHead || !table.tBodies.length) return;
            const headers = Array.from(table.tHead.rows);
            // Multi-level headers and merged body cells need their original grid.
            const labels = Array.from(headers[headers.length - 1].cells).map(cell => cell.textContent.trim());
            const rows = Array.from(table.tBodies).flatMap(body => Array.from(body.rows));
            const simple = headers.length === 1 && Array.from(headers[0].cells).every(cell => cell.colSpan === 1 && cell.rowSpan === 1)
                && rows.every(row => Array.from(row.cells).every(cell => cell.rowSpan === 1 && (cell.colSpan === 1 || row.cells.length === 1)));
            table.classList.toggle('ims-mobile-table', simple);
            container.classList.toggle('ims-stacked-container', simple);
            if (simple) {
                let owner = container.parentElement;
                while (owner && !owner.matches('main, .main-content, body')) {
                    if (owner.matches('.card, .card-body, .data-table-wrapper, .dataTables_wrapper')) owner.classList.add('ims-table-owner');
                    owner = owner.parentElement;
                }
                rows.forEach(function (row) {
                    Array.from(row.cells).forEach(function (cell, index) {
                        if (row.cells.length !== labels.length) {
                            cell.removeAttribute('data-ims-label');
                        } else if (cell.dataset.imsLabel !== labels[index]) {
                            cell.dataset.imsLabel = labels[index];
                        }
                    });
                });
            }
        });
    }

    let scheduled = false;
    const observer = new MutationObserver(function (changes) {
        if (scheduled || !changes.some(change => change.type === 'childList')) return;
        scheduled = true;
        requestAnimationFrame(function () { scheduled = false; prepareTables(); });
    });
    prepareTables();
    observer.observe(document.body, { childList: true, subtree: true });
    if (window.jQuery) window.jQuery(document).on('draw.dt', prepareTables);
})();
