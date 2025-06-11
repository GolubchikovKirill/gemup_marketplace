export function autoResizeTextareas() {
  document.addEventListener('DOMContentLoaded', function () {
    const textareas = document.querySelectorAll('textarea');
    if (!textareas.length) return;

    textareas.forEach(textarea => {
      textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
      });

      if (textarea.value.trim() !== '') {
        textarea.style.height = textarea.scrollHeight + 'px';
      }
    });
  });
}