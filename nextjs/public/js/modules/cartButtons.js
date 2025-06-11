export function setupCartButtons() {
  document.addEventListener('DOMContentLoaded', function () {
    const cards = document.querySelectorAll('.buttom');
    if (!cards.length) return;

    cards.forEach(card => {
      const cartButton = card.querySelector('.order__action > button');
      const icon = cartButton?.querySelector('i');
      const counter = card.querySelector('.order__counter');
      const minusBtn = counter?.querySelector('button:first-child');
      const plusBtn = counter?.querySelector('button:last-child');
      const input = counter?.querySelector('input');
      const priceValue = card.querySelector('.price .value');

      if (!cartButton || !icon || !counter || !minusBtn || !plusBtn || !input || !priceValue) return;

      let unitPrice = parseFloat(priceValue.textContent.replace(',', '.'));

      function updatePrice(qty) {
        const total = (qty * unitPrice).toFixed(2).replace('.', ',');
        priceValue.textContent = total;
      }

      cartButton.addEventListener('click', () => {
        counter.classList.toggle('active');
        icon.classList.toggle('ico-cart');
        icon.classList.toggle('ico-done');
      });

      minusBtn.addEventListener('click', function (e) {
        e.preventDefault();
        let current = parseInt(input.value) || 1;
        if (current > 1) current--;
        input.value = current;
        updatePrice(current);
      });

      plusBtn.addEventListener('click', function (e) {
        e.preventDefault();
        let current = parseInt(input.value) || 1;
        current++;
        input.value = current;
        updatePrice(current);
      });

      input.value = 1;
      updatePrice(1);
    });
  });
}