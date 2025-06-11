export function setupTariffSelect() {
  document.addEventListener('DOMContentLoaded', function () {
    const tariffRadios = document.querySelectorAll('input[name="tariff"]');
    const quantityInput = document.querySelector('.counter input');
    const minusBtn = document.querySelector('.counter button:first-child');
    const plusBtn = document.querySelector('.counter button:last-child');
    const priceOutput = document.querySelector('.item__price .value');

    if (!tariffRadios.length || !quantityInput || !minusBtn || !plusBtn || !priceOutput) return;

    let currentUnitPrice = 0;

    function formatPrice(price) {
      return price.toLocaleString("ru-RU", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
    }

    function getQuantity() {
      const raw = quantityInput.value.replace(/\D/g, '');
      return raw ? parseInt(raw) : 1;
    }

    function updateTotal() {
      const quantity = getQuantity();
      const total = quantity * currentUnitPrice;
      priceOutput.textContent = formatPrice(total);
    }

    function setUnitPriceFromRadio(radio) {
      const label = radio.closest('label');
      let priceText = label.querySelector('.bottom .value')?.textContent || radio.dataset.price;
      if (priceText) {
        currentUnitPrice = parseFloat(priceText.replace(',', '.'));
        quantityInput.value = 1;
        updateTotal();
      }
    }

    tariffRadios.forEach(radio => {
      radio.addEventListener('change', function () {
        setUnitPriceFromRadio(this);
      });

      if (radio.checked) {
        setUnitPriceFromRadio(radio);
      }
    });

    minusBtn.addEventListener('click', () => {
      let quantity = getQuantity();
      if (quantity > 1) {
        quantity--;
        quantityInput.value = quantity;
        updateTotal();
      }
    });

    plusBtn.addEventListener('click', () => {
      let quantity = getQuantity();
      quantity++;
      quantityInput.value = quantity;
      updateTotal();
    });

    quantityInput.addEventListener('input', () => updateTotal());
    updateTotal();
  });
}