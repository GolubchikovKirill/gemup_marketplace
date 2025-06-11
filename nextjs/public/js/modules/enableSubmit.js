export function enableSubmitWhenAllRequiredFieldsFilled() {
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(form => {
      const requiredFields = form.querySelectorAll('input[required]');
      const submitButton = form.querySelector('button[type="submit"]');
      if (!submitButton || !requiredFields.length) return;

      const checkValidity = () => {
        const allFilled = Array.from(requiredFields).every(input => input.value.trim() !== '');
        submitButton.disabled = !allFilled;
      };

      requiredFields.forEach(input => input.addEventListener('input', checkValidity));
      checkValidity(); // на случай автозаполнения
    });
  });
}