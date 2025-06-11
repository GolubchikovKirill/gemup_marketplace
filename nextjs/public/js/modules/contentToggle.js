export function setupContentToggle() {
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.content__area').forEach(area => {
      const toggleBtn = area.querySelector('.openContent');
      const subContent = area.querySelector('.sub__content');
      if (!toggleBtn || !subContent) return;

      toggleBtn.addEventListener('click', () => {
        const isActive = subContent.classList.toggle('active');
        area.classList.toggle('open', isActive);
      });
    });
  });
}