export function initDropdown() {
  document.addEventListener("DOMContentLoaded", () => {
    const dropdownList = document.querySelectorAll(".dropdown");
    const classList = {
      dropdown: {
        active: "dropdown--active",
        disabled: "dropdown--disabled",
      },
      trigger: "dropdown__toggle",
      triggerText: "dropdown__toggle span",
      item: "dropdown__menu-item"
    };

    dropdownList.forEach((dropdown) => {
      dropdown.addEventListener("click", (e) => {
        if (
          (!dropdown.classList.contains(classList.dropdown.disabled) &&
            e.target.classList.contains(classList.trigger)) ||
          e.target.parentElement.classList.contains(classList.trigger)
        ) {
          dropdown.classList.toggle(classList.dropdown.active);
        }

        if (
          dropdown.classList.contains(classList.dropdown.active) &&
          e.target.classList.contains(classList.item)
          // e.target.parentElement.classList.contains(classList.item)
        ) {
          const triggerText = dropdown.querySelector(`.${classList.triggerText}`);
          triggerText.textContent = e.target.textContent;
          dropdown.classList.remove(classList.dropdown.active);
        }
      });
    });
  });
}
