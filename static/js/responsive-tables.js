(function () {
    'use strict';

    function updateLayout(container) {
        const compact = container.clientWidth <= 640;
        const table = container.querySelector('table.ims-mobile-table');
        container.classList.toggle('ims-card-container', compact && !!table);
        if (table) table.classList.toggle('ims-card-layout', compact);
        const sort = container.querySelector('.ims-table-sort');
        if (sort) sort.classList.toggle('is-compact', compact && !!table);
        document.querySelectorAll('.ims-table-owner').forEach(function (owner) {
            owner.classList.toggle('is-compact', !!owner.querySelector('.ims-card-layout'));
        });
    }

    const sizes = new ResizeObserver(entries => entries.forEach(entry => updateLayout(entry.target)));
    const observed = new WeakSet();

    function prepareSorting(table, container, labels) {
        if (!window.jQuery || !window.jQuery.fn.dataTable || !window.jQuery.fn.dataTable.isDataTable(table)) return;
        const api = window.jQuery(table).DataTable();
        let control = container.querySelector('.ims-table-sort');
        if (!control) {
            control = document.createElement('div');
            control.className = 'ims-table-sort';
            const label = document.createElement('label');
            const select = document.createElement('select');
            select.className = 'form-select form-select-sm';
            select.setAttribute('aria-label', 'Sort records');
            label.textContent = 'Sort by';
            label.appendChild(select);
            api.settings()[0].aoColumns.forEach(function (column, index) {
                if (!column.bSortable) return;
                ['asc', 'desc'].forEach(function (direction) {
                    select.add(new Option(labels[index] + ' (' + (direction === 'asc' ? 'ascending' : 'descending') + ')', index + ':' + direction));
                });
            });
            select.addEventListener('change', function () {
                const [index, direction] = select.value.split(':');
                api.order([Number(index), direction]).draw();
            });
            control.appendChild(label);
            container.prepend(control);
        }
        const order = api.order()[0];
        if (order) control.querySelector('select').value = order.join(':');
    }

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
            if (!observed.has(container)) { sizes.observe(container); observed.add(container); }
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
                const primary = labels.findIndex(label => /^(student|name|user|internship|organisation|organization|programme|program|batch|component|title|mentor)(\s|$)/i.test(label));
                let owner = container.parentElement;
                while (owner && !owner.matches('main, .main-content, body')) {
                    if (owner.matches('.card, .card-body, .data-table-wrapper, .dataTables_wrapper')) owner.classList.add('ims-table-owner');
                    owner = owner.parentElement;
                }
                rows.forEach(function (row) {
                    Array.from(row.cells).forEach(function (cell, index) {
                        cell.classList.toggle('ims-primary-field', row.cells.length === labels.length && index === (primary < 0 ? 0 : primary));
                        if (row.cells.length !== labels.length) {
                            cell.removeAttribute('data-ims-label');
                        } else if (cell.dataset.imsLabel !== labels[index]) {
                            cell.dataset.imsLabel = labels[index];
                        }
                    });
                });
                prepareSorting(table, container, labels);
            }
            updateLayout(container);
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
