export function initTabs() {
  document.addEventListener('DOMContentLoaded', function () {
    const tabButtons = document.querySelectorAll('.tabs__button');
    const tabContents = document.querySelectorAll('.tab');

    if (!tabButtons.length || !tabContents.length) return;

    tabButtons.forEach(button => {
      button.addEventListener('click', function () {
        const target = this.dataset.tab;

        tabButtons.forEach(btn => btn.classList.remove('active'));
        this.classList.add('active');

        tabContents.forEach(tab => {
          tab.classList.toggle('active', tab.id === target);
        });
      });
    });
  });
}