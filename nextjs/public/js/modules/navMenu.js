document.addEventListener('DOMContentLoaded', function () {
  const burger = document.querySelector('.burger__wrapper');
  const mobileMenu = document.querySelector('.mobileMenu__wrapper');
  const closeBtn = mobileMenu.querySelector('.closeMenu');
  const body = document.body;

  // Открыть меню
  burger.addEventListener('click', function () {
    mobileMenu.classList.add('active');
    body.classList.add('bodyScroll'); // Отключаем скролл
  });

  // Закрыть меню
  closeBtn.addEventListener('click', function () {
    mobileMenu.classList.remove('active');
    body.classList.remove('bodyScroll'); // Возвращаем скролл
  });
});
