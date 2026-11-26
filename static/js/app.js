
document.addEventListener('DOMContentLoaded', () => {

    // =========================================================
    // 1. MOBILE SIDEBAR TOGGLE
    // =========================================================

    const menuBtn = document.querySelector('.topbar__menu-btn');
    const overlay = document.querySelector('.sidebar-overlay');
    const layout = document.querySelector('.layout');
    const sidebar = document.querySelector('.sidebar');

    function setSidebarOpen(isOpen) {

        if (!layout) return;

        layout.classList.toggle(
            'layout--sidebar-open',
            isOpen
        );

        if (menuBtn) {
            menuBtn.setAttribute(
                'aria-expanded',
                String(isOpen)
            );
        }
    }

    if (menuBtn && layout) {

        // Initialise the accessibility state.
        setSidebarOpen(
            layout.classList.contains('layout--sidebar-open')
        );

        // Allow the menu button to open and close the sidebar.
        menuBtn.addEventListener('click', () => {

            const isOpen = !layout.classList.contains(
                'layout--sidebar-open'
            );

            setSidebarOpen(isOpen);

        });

    }

    // Close sidebar when the overlay is clicked.
    if (overlay) {

        overlay.addEventListener('click', () => {
            setSidebarOpen(false);
        });

    }

    // Close sidebar when a navigation link is selected.
    if (sidebar) {

        sidebar.querySelectorAll('a').forEach((link) => {

            link.addEventListener('click', () => {
                setSidebarOpen(false);
            });

        });

    }

    // Close sidebar with Escape.
    document.addEventListener('keydown', (event) => {

        if (event.key === 'Escape' && layout) {
            setSidebarOpen(false);
        }

    });


    // =========================================================
    // 2. GLOBAL RESPONSIVE TABLE WRAPPER
    // =========================================================

    // Every table is wrapped unless explicitly excluded.
    // Add data-no-scroll to tables that should not be wrapped.

    const TABLE_SELECTOR = 'table:not([data-no-scroll])';

    function wrapTable(table) {

        if (!table || !table.parentNode) return;

        // Avoid duplicate wrappers.
        let wrapper = table.closest('.table-responsive');

        // Create a wrapper if one does not already exist.
        if (!wrapper) {

            wrapper = document.createElement('div');

            wrapper.className = 'table-responsive';

            table.parentNode.insertBefore(wrapper, table);

            wrapper.appendChild(table);

        }

        // Make the scrolling region keyboard accessible.
        wrapper.setAttribute('role', 'region');

        wrapper.setAttribute('tabindex', '0');

        // Preserve an existing descriptive label where possible.
        const caption = table.querySelector('caption');

        const label =
            table.dataset.scrollLabel ||
            table.getAttribute('aria-label') ||
            caption?.textContent.trim() ||
            'Scrollable data table';

        wrapper.setAttribute('aria-label', label);

    }


    // Process all tables currently present in the document.
    document.querySelectorAll(TABLE_SELECTOR).forEach(wrapTable);


    // =========================================================
    // 3. MUTATION OBSERVER FOR DYNAMICALLY ADDED TABLES
    // =========================================================

    function processAddedNode(node) {

        // Only process HTML elements.
        if (node.nodeType !== Node.ELEMENT_NODE) return;

        // Check whether the newly added element is itself a table.
        if (node.matches(TABLE_SELECTOR)) {
            wrapTable(node);
        }

        // Check for tables inside the newly added element.
        node.querySelectorAll(TABLE_SELECTOR).forEach(wrapTable);

    }


    const observer = new MutationObserver((mutations) => {

        mutations.forEach((mutation) => {

            mutation.addedNodes.forEach(processAddedNode);

        });

    });


    // Monitor the entire document for new tables.
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });


    // =========================================================
    // 4. DYNAMIC RECEIPT / SALES FORM ROWS
    // =========================================================

    // Support both the original and alternative container IDs.
    const container = document.querySelector(
        '#lines-container, #form-lines-container'
    );

    const addBtn = document.querySelector('#add-line-btn');

    const template = document.querySelector('#line-template');


    if (container && addBtn && template) {

        const form = container.closest('form');

        // Detect the Django formset prefix from __prefix__.
        const templateField = template.content.querySelector(
            '[name*="__prefix__"]'
        );

        const prefixMatch = templateField
            ? templateField.name.match(/^(.+?)-__prefix__-/)
            : null;

        const formsetPrefix = prefixMatch
            ? prefixMatch[1]
            : null;


        // Locate the corresponding Django TOTAL_FORMS field.
        const totalFormsInputs = form
            ? Array.from(
                form.querySelectorAll(
                    'input[name$="-TOTAL_FORMS"]'
                )
            )
            : [];

        const totalFormsInput = formsetPrefix
            ? totalFormsInputs.find(
                input => input.name === `${formsetPrefix}-TOTAL_FORMS`
            )
            : totalFormsInputs.length === 1
                ? totalFormsInputs[0]
                : null;


        // Escape the prefix before using it in a regular expression.
        function escapeRegExp(value) {

            return value.replace(
                /[.*+?^${}()|[\]\\]/g,
                '\\$&'
            );

        }


        const prefixPattern = formsetPrefix
            ? new RegExp(
                `^${escapeRegExp(formsetPrefix)}-(\\d+)-`
            )
            : null;


        // Determine the next valid formset index.
        function getNextRowIndex() {

            let maxIndex = -1;

            if (prefixPattern) {

                container.querySelectorAll('[name]').forEach((field) => {

                    const match = field.name.match(prefixPattern);

                    if (match) {
                        maxIndex = Math.max(
                            maxIndex,
                            Number(match[1])
                        );
                    }

                });

            }

            const existingCount = totalFormsInput
                ? Number(totalFormsInput.value) || 0
                : 0;

            const visibleRowCount = container.querySelectorAll(
                '.dynamic-row'
            ).length;

            return Math.max(
                maxIndex + 1,
                existingCount,
                visibleRowCount
            );

        }


        let rowCount = getNextRowIndex();


        // Keep Django's formset management field synchronised.
        function updateTotalForms(value) {

            if (totalFormsInput) {
                totalFormsInput.value = String(value);
            }

        }


        // Reindex remaining rows when a row is physically removed.
        function reindexRows() {

            const rows = Array.from(
                container.querySelectorAll('.dynamic-row')
            );

            if (!prefixPattern) {

                rowCount = rows.length;
                updateTotalForms(rowCount);

                return;

            }

            const referenceAttributes = [
                'name',
                'id',
                'for',
                'aria-describedby',
                'aria-labelledby',
                'aria-controls'
            ];

            rows.forEach((row, newIndex) => {

                const firstNamedField = row.querySelector('[name]');

                if (!firstNamedField) return;

                const match = firstNamedField.name.match(
                    prefixPattern
                );

                if (!match) return;

                const oldIndex = match[1];

                const oldToken =
                    `${formsetPrefix}-${oldIndex}-`;

                const newToken =
                    `${formsetPrefix}-${newIndex}-`;


                row.querySelectorAll(
                    '[name], [id], [for], [aria-describedby], ' +
                    '[aria-labelledby], [aria-controls]'
                ).forEach((element) => {

                    referenceAttributes.forEach((attribute) => {

                        const value = element.getAttribute(attribute);

                        if (value && value.includes(oldToken)) {

                            element.setAttribute(
                                attribute,
                                value.split(oldToken).join(newToken)
                            );

                        }

                    });

                });

            });

            rowCount = rows.length;

            updateTotalForms(rowCount);

        }


        // Add a new receipt or sales line.
        addBtn.addEventListener('click', (event) => {

            event.preventDefault();

            // Clone the Django empty-form template.
            const clone = template.content.cloneNode(true);

            // Replace the Django __prefix__ placeholder.
            const replacePrefix = (value) => {

                return value.replace(
                    /__prefix__/g,
                    String(rowCount)
                );

            };


            // Update input names, IDs and associated references.
            const referenceAttributes = [
                'name',
                'id',
                'for',
                'aria-describedby',
                'aria-labelledby',
                'aria-controls'
            ];

            clone.querySelectorAll(
                '[name], [id], [for], [aria-describedby], ' +
                '[aria-labelledby], [aria-controls]'
            ).forEach((element) => {

                referenceAttributes.forEach((attribute) => {

                    const value = element.getAttribute(attribute);

                    if (value) {
                        element.setAttribute(
                            attribute,
                            replacePrefix(value)
                        );
                    }

                });

            });


            // Attach row removal behaviour.
            const removeBtn = clone.querySelector(
                '.btn-remove-row'
            );

            if (removeBtn) {

                removeBtn.addEventListener('click', (removeEvent) => {

                    removeEvent.preventDefault();

                    const row = removeBtn.closest('.dynamic-row');

                    if (!row) return;

                    // If Django supports deletion, mark the form for deletion.
                    const deleteField = row.querySelector(
                        'input[name$="-DELETE"]'
                    );

                    if (deleteField) {

                        deleteField.checked = true;

                        row.hidden = true;

                        return;

                    }

                    // Otherwise remove and reindex the remaining rows.
                    row.remove();

                    reindexRows();

                });

            }


            // Insert the new row.
            container.appendChild(clone);

            rowCount++;

            // Inform Django that another form exists.
            updateTotalForms(rowCount);

        });

    }

});
