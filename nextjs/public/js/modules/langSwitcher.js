document.addEventListener('DOMContentLoaded', function () {
  const langSwitchBlocks = document.querySelectorAll('.lang__switch');
  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

  langSwitchBlocks.forEach(langSwitch => {
    const currentLang = langSwitch.querySelector('.currect__lang');
    const langList = langSwitch.querySelector('.lang__list ul');
    const langItems = langSwitch.querySelectorAll('.lang__item');

    function selectLanguage(item) {
      // Удаляем active у всех внутри текущего блока
      langItems.forEach(el => el.classList.remove('active'));
      // Назначаем active выбранному элементу
      item.classList.add('active');
      // Обновляем текст текущего языка
      currentLang.querySelector('span').textContent = item.textContent;
      // Скрываем список
      langList.classList.remove('active');
    }

    if (isMobile) {
      currentLang.addEventListener('click', function (e) {
        langList.classList.toggle('active');
        e.stopPropagation();
      });

      langItems.forEach(item => {
        item.addEventListener('click', function () {
          selectLanguage(item);
        });
      });

      document.addEventListener('click', function (e) {
        if (!langSwitch.contains(e.target)) {
          langList.classList.remove('active');
        }
      });
    } else {
      langSwitch.addEventListener('mouseenter', function () {
        langList.classList.add('active');
      });

      langSwitch.addEventListener('mouseleave', function () {
        langList.classList.remove('active');
      });

      langItems.forEach(item => {
        item.addEventListener('click', function () {
          selectLanguage(item);
        });
      });
    }
  });
});
