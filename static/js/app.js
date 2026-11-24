document.addEventListener('DOMContentLoaded', () => {
  // 1. Handle Dynamic Form Rows
  const container = document.getElementById('form-lines-container');
  const addBtn = document.getElementById('add-line-btn');

  if (container && addBtn) {
    let rowCount = 1;

    addBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const template = document.getElementById('line-template');
      const clone = template.content.cloneNode(true);

      // Update names and IDs to prevent Django form clashes
      clone.querySelectorAll('[name]').forEach(input => {
        input.name = input.name.replace('__prefix__', rowCount);
      });
      clone.querySelectorAll('[id]').forEach(input => {
        input.id = input.id.replace('__prefix__', rowCount);
      });

      // Add remove functionality
      const removeBtn = clone.querySelector('.btn-remove-row');
      removeBtn.addEventListener('click', (ev) => {
        ev.preventDefault();
        ev.target.closest('.dynamic-row').remove();
      });

      container.appendChild(clone);
      rowCount++;
    });
  }

  // 2. Mobile Sidebar Toggle
  const menuBtn = document.querySelector('.topbar__menu-btn');
  const overlay = document.querySelector('.sidebar-overlay');

  if (menuBtn) {
    menuBtn.addEventListener('click', () => {
      document.querySelector('.layout').classList.toggle('layout--sidebar-open');
    });
  }
  if (overlay) {
    overlay.addEventListener('click', () => {
      document.querySelector('.layout').classList.remove('layout--sidebar-open');
    });
  }
});