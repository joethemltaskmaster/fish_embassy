
document.addEventListener('DOMContentLoaded', () => {

    // =========================================================
    // 1. GLOBAL TABLE SCROLL FIX
    // =========================================================
    // Automatically wraps tables in a responsive scrolling container.

    const tables = document.querySelectorAll('table.table');

    tables.forEach((table) => {

        // Avoid wrapping a table that is already responsive.
        if (!table.parentElement?.classList.contains('table-responsive')) {

            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';

            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });


    // =========================================================
    // 2. DYNAMIC RECEIPT LINE ITEMS
    // =========================================================

    // These selectors must match the IDs in your HTML template.
    const container = document.querySelector('#lines-container');
    const addBtn = document.querySelector('#add-line-btn');
    const template = document.querySelector('#line-template');

    if (container && addBtn && template) {

        // Start after the existing rows to avoid duplicate indexes.
        let rowCount = container.querySelectorAll('.dynamic-row').length;

        addBtn.addEventListener('click', (event) => {

            event.preventDefault();

            // Clone the HTML template.
            const clone = template.content.cloneNode(true);

            // Update Django field names.
            clone.querySelectorAll('[name]').forEach((input) => {

                input.name = input.name.replace(
                    /__prefix__/g,
                    rowCount
                );

            });

            // Update element IDs.
            clone.querySelectorAll('[id]').forEach((element) => {

                element.id = element.id.replace(
                    /__prefix__/g,
                    rowCount
                );

            });

            // Update label references.
            clone.querySelectorAll('[for]').forEach((label) => {

                label.htmlFor = label.htmlFor.replace(
                    /__prefix__/g,
                    rowCount
                );

            });

            // Attach remove functionality.
            const removeBtn = clone.querySelector('.btn-remove-row');

            if (removeBtn) {

                removeBtn.addEventListener('click', (event) => {

                    event.preventDefault();

                    // Remove the entire dynamic row.
                    const row = removeBtn.closest('.dynamic-row');

                    if (row) {
                        row.remove();
                    }

                });

            }

            // Add the new row to the container.
            container.appendChild(clone);

            rowCount++;

        });

    }


    // =========================================================
    // 3. MOBILE SIDEBAR TOGGLE
    // =========================================================

    const menuBtn = document.querySelector('.topbar__menu-btn');
    const overlay = document.querySelector('.sidebar-overlay');
    const layout = document.querySelector('.layout');

    // Open and close the sidebar using the menu button.
    if (menuBtn && layout) {

        menuBtn.addEventListener('click', () => {

            const isOpen = layout.classList.toggle(
                'layout--sidebar-open'
            );

            menuBtn.setAttribute(
                'aria-expanded',
                String(isOpen)
            );

        });

    }

    // Close the sidebar when the overlay is clicked.
    if (overlay && layout) {

        overlay.addEventListener('click', () => {

            layout.classList.remove('layout--sidebar-open');

            if (menuBtn) {
                menuBtn.setAttribute('aria-expanded', 'false');
            }

        });

    }

});
