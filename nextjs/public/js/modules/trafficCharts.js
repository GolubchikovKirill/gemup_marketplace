// app.js
export function initTrafficCharts() {
  // Ждём, пока DOM загрузится
  document.addEventListener('DOMContentLoaded', () => {
    // Находим все контейнеры с графиками
    const wrappers = document.querySelectorAll('.Canv__wrapper');
    if (!wrappers.length) return;

    const charts = [];

    wrappers.forEach(container => {
      const canvas = container.querySelector('canvas');
      if (!canvas) return;

      const ctx = canvas.getContext('2d');

      const maxValue = parseFloat(canvas.dataset.max) || 100;
      const targetValue = parseFloat(canvas.dataset.value) || 0;
      const line1 = canvas.dataset.line1 || 'Traffic used';
      const gbTotal = canvas.dataset.total || '/ 10 gb';

      let animatedValue = 0;
      let width, height, centerX, centerY, radius, lineWidth;

      function resizeCanvas() {
        const size = container.offsetWidth;
        canvas.width = size;
        canvas.height = size;

        width = canvas.width;
        height = canvas.height;
        centerX = width / 2;
        centerY = height / 2;
        radius = width * 0.4;
        lineWidth = width * 0.075;

        animatedValue = 0;
        animateChart();
      }

      function drawChart(value) {
        ctx.clearRect(0, 0, width, height);

        // Фон круга
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = '#0F1721';
        ctx.lineWidth = lineWidth;
        ctx.stroke();

        if (value > 0) {
          const startAngle = -Math.PI / 2;
          const endAngle = startAngle + (value / maxValue) * 2 * Math.PI;

          ctx.beginPath();
          ctx.arc(centerX, centerY, radius, startAngle, endAngle);
          ctx.strokeStyle = '#4caf50';
          ctx.lineWidth = lineWidth;
          ctx.lineCap = 'round';
          ctx.stroke();

          // Точка на конце прогресса
          const dotRadius = lineWidth * 0.65;
          const dotX = centerX + radius * Math.cos(endAngle);
          const dotY = centerY + radius * Math.sin(endAngle);

          ctx.beginPath();
          ctx.arc(dotX, dotY, dotRadius, 0, 2 * Math.PI);
          ctx.fillStyle = '#B3FFDF';
          ctx.strokeStyle = '#4caf50';
          ctx.lineWidth = lineWidth * 0.2;
          ctx.fill();
          ctx.stroke();
        }

        // Текст
        const usedGb = (value / 100).toFixed(2);
        const gbValue = `${usedGb} `;

        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        ctx.fillStyle = '#fff';
        ctx.font = `300 ${Math.floor(width * 0.045)}px Inter`;
        ctx.fillText(line1, centerX, centerY - width * 0.05);

        const fontSize = Math.floor(width * 0.075);
        ctx.font = `700 ${fontSize}px Inter`;

        const gbValueWidth = ctx.measureText(gbValue).width;
        const totalWidth = ctx.measureText(gbTotal).width;
        const totalTextX = centerX + gbValueWidth / 2;
        const valueTextX = centerX - totalWidth / 2;

        ctx.fillStyle = '#13F195';
        ctx.fillText(gbValue, valueTextX, centerY + width * 0.05);

        ctx.fillStyle = '#fff';
        ctx.fillText(gbTotal, totalTextX, centerY + width * 0.05);
      }

      function animateChart() {
        const speed = 40;
        if (animatedValue < targetValue) {
          animatedValue += (targetValue - animatedValue) / speed;
          if (targetValue - animatedValue < 1) {
            animatedValue = targetValue;
          }
          drawChart(animatedValue);
          requestAnimationFrame(animateChart);
        } else {
          drawChart(targetValue);
        }
      }

      charts.push(resizeCanvas);

      resizeCanvas();
    });

    // Перерисовываем все графики при ресайзе окна
    window.addEventListener('resize', () => {
      charts.forEach(fn => fn());
    });
  });
}
