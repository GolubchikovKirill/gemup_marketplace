export function setupFilterTabs() {
  document.addEventListener('DOMContentLoaded', function () {
    const tabButtons = document.querySelectorAll('.tabs__button');
    const contentElements = document.querySelectorAll('.table__content > div');

    if (!tabButtons.length || !contentElements.length) return;

    function showCategory(category) {
      contentElements.forEach(el => {
        const categories = (el.dataset.category || '').split(' ');
        el.style.display = categories.includes(category) ? '' : 'none';
      });
    }

    tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        tabButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        showCategory(button.dataset.tab);
      });
    });

    // Инициализация — активируем первую вкладку
    tabButtons[0].click();
  });
}