export function plusMinus() {
  document.addEventListener("DOMContentLoaded", () => {
    const minus = document.querySelectorAll("#minus");
    const plus = document.querySelectorAll("#plus");
    const input = document.querySelector("#generate-proxy-count-input");

    const updateInputValue = (inputSelector, operator) => {
      const input = document.querySelector(inputSelector);
      const currentValue = +input.value;
      if (currentValue <= 0) {
        return;
      }

      if (operator === "+") {
        input.value = currentValue + 1;
      }

      if (operator === "-") {
        input.value = currentValue - 1;
      }
    };

    try {
      minus.forEach((item) =>
        item.addEventListener("click", () =>
          updateInputValue(`#${item.dataset.inputId}`, "-")
        )
      );
      plus.forEach((item) =>
        item.addEventListener("click", () =>
          updateInputValue(`#${item.dataset.inputId}`, "+")
        )
      );

      input.addEventListener("input", () => {
        if (+input.value <= 0) {
          input.value = 0;
        }

        input.value = parseInt(input.value);
      });
    } catch (e) {}
  });
}
