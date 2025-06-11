export function setupGenCopy() {
  document.addEventListener('DOMContentLoaded', () => {
    const copyButton = document.querySelector('.genCopy');
    if (!copyButton) return;

    copyButton.addEventListener('click', () => {
      const values = Array.from(document.querySelectorAll('.generated__list .value'))
        .map(el => el.textContent.trim())
        .join('\n');

      if (!values) return;

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(values).then(() => showCopied(copyButton));
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = values;
        textarea.style.position = 'fixed';
        textarea.style.opacity = 0;
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        try {
          document.execCommand('copy');
          showCopied(copyButton);
        } catch (err) {
          console.error('execCommand error:', err);
        }
        document.body.removeChild(textarea);
      }
    });

    function showCopied(button) {
      const original = button.innerHTML;
      button.innerHTML = 'Copied! <i class="ico-copy"></i>';
      setTimeout(() => {
        button.innerHTML = original;
      }, 2000);
    }
  });
}