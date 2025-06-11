// cart.js
export function initCart() {
  document.addEventListener("DOMContentLoaded", () => {
    const cartWrapper = document.querySelector(".cartProducts__wrapper");
    const totalValueEl = document.querySelector(".price__data .value");
    const cartCountElement = document.querySelector('.form__header .value');

    if (!cartWrapper || !totalValueEl) return;

    function updateTotal() {
      let total = 0;

      cartWrapper.querySelectorAll(".cart__item").forEach(item => {
        const priceEl = item.querySelector(".price .value");
        const basePrice = parseFloat(priceEl.dataset.basePrice);
        const quantity = parseInt(item.querySelector(".order__counter input").value) || 1;

        const itemTotal = basePrice * quantity;
        priceEl.textContent = itemTotal.toFixed(2);
        total += itemTotal;
      });

      totalValueEl.textContent = total.toFixed(2);
    }

    function updateCartItemCount() {
      const cartItems = cartWrapper.querySelectorAll('.cart__item');
      const itemCount = cartItems.length;
      if (cartCountElement) {
        cartCountElement.textContent = itemCount;
      }
    }

    function updateAll() {
      updateTotal();
      updateCartItemCount();
    }

    function setupItem(item) {
      const minusBtn = item.querySelector(".order__counter button:first-child");
      const plusBtn = item.querySelector(".order__counter button:last-child");
      const input = item.querySelector(".order__counter input");
      const priceEl = item.querySelector(".price .value");
      const deleteBtn = item.querySelector("button.deleteProd");

      if (!priceEl.dataset.basePrice) {
        priceEl.dataset.basePrice = parseFloat(priceEl.textContent);
      }

      minusBtn.addEventListener("click", () => {
        let current = parseInt(input.value) || 1;
        if (current > 1) {
          input.value = current - 1;
          updateAll();
        }
      });

      plusBtn.addEventListener("click", () => {
        let current = parseInt(input.value) || 1;
        input.value = current + 1;
        updateAll();
      });

      input.addEventListener("input", () => {
        let value = parseInt(input.value);
        if (isNaN(value) || value < 1) {
          input.value = 1;
        }
        updateAll();
      });

      deleteBtn.addEventListener("click", () => {
        item.remove();
        updateAll();
      });
    }

    cartWrapper.querySelectorAll(".cart__item").forEach(setupItem);

    updateAll();
  });
}