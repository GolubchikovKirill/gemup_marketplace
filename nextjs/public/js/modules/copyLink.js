export function setupCopyLink() {
  document.addEventListener('DOMContentLoaded', function () {
    const copyButton = document.querySelector('.copy-link');
    if (!copyButton) return;

    copyButton.addEventListener('click', function () {
      const url = window.location.href;

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(url).then(() => showCopied(copyButton));
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = url;
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
      button.innerHTML = '<i class="ico-copy"></i>Copied!';
      setTimeout(() => {
        button.innerHTML = original;
      }, 2000);
    }
  });
}