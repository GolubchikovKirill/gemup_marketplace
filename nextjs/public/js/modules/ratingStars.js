export function initRatingStars() {
  document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('addReview');
    if (!modal) return;

    const starsContainer = modal.querySelector('.rating__stars');
    const stars = starsContainer.querySelectorAll('.ico-star');
    const valueDisplay = modal.querySelector('.rating__wrapper .value');
    const hiddenInput = modal.querySelector('input[name="rating"]');
    const submitButton = modal.querySelector('button[type="submit"]');

    function updateStars(rating) {
      stars.forEach(star => {
        const val = parseInt(star.getAttribute('data-value'));
        star.classList.toggle('active', val <= rating);
      });
    }

    stars.forEach(star => {
      star.addEventListener('click', () => {
        const rating = parseInt(star.getAttribute('data-value'));
        updateStars(rating);
        hiddenInput.value = rating;
        valueDisplay.textContent = rating.toFixed(1);
        submitButton.disabled = rating === 0;
      });

      star.addEventListener('mouseenter', () => {
        const hoverRating = parseInt(star.getAttribute('data-value'));
        updateStars(hoverRating);
      });

      star.addEventListener('mouseleave', () => {
        const currentRating = parseInt(hiddenInput.value) || 0;
        updateStars(currentRating);
      });
    });
  });
}