export function toggleDescription() {
  document.addEventListener('DOMContentLoaded', function () {
    const toggleButton = document.querySelector('#description__block button');
    const contentBody = document.querySelector('#description__block .content__body');

    if (!toggleButton || !contentBody) return;

    let expanded = false;

    toggleButton.addEventListener('click', () => {
      expanded = !expanded;
      contentBody.classList.toggle('active', expanded);
      toggleButton.textContent = expanded ? "Hidden" : "More";
    });
  });
}