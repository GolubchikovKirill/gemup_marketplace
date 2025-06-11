export function setupProductFilters() {
  const filterContainer = document.querySelector('.product__filters');
  const productContainer = document.querySelector('#products__container');

  if (!filterContainer || !productContainer) return;

  const filterButtons = filterContainer.querySelectorAll('.filter-btn');
  const seeAllButton = filterContainer.querySelector('.see-all');
  const categories = productContainer.querySelectorAll('.product__category');

  const activeFilters = new Set();

  // Обновление отображения категорий
  function updateCategoryVisibility() {
    categories.forEach(category => {
      const tags = category.dataset.tags?.split(/\s+/) || [];

      const hasMatch =
        activeFilters.size === 0 ||
        [...activeFilters].some(filter => tags.includes(filter));

      category.style.display = hasMatch ? '' : 'none';
    });
  }

  // Обработка кликов по фильтрам
  filterButtons.forEach(button => {
    button.addEventListener('click', () => {
      const filter = button.dataset.filter;

      if (activeFilters.has(filter)) {
        activeFilters.delete(filter);
        button.classList.remove('active');
      } else {
        activeFilters.add(filter);
        button.classList.add('active');
      }

      updateCategoryVisibility();
    });
  });

  // Кнопка "See all" — сброс
  if (seeAllButton) {
    seeAllButton.addEventListener('click', () => {
      activeFilters.clear();
      filterButtons.forEach(btn => btn.classList.remove('active'));
      updateCategoryVisibility();
    });
  }

  // Инициализация
  updateCategoryVisibility();
}
