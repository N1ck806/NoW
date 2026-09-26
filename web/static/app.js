/* Nightmare Dashboard — JS */

window.renderGamesChart = function (data) {
    const canvas = document.getElementById('gamesChart');
    if (!canvas || !data || data.length === 0) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = 250;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const maxValue = Math.max(...data.map(d => d.count), 1);
    const barWidth = chartWidth / data.length * 0.7;
    const gap = chartWidth / data.length * 0.3;

    ctx.strokeStyle = '#2b2f38';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, height - padding);
    ctx.lineTo(width - padding, height - padding);
    ctx.stroke();

    data.forEach((item, i) => {
        const barHeight = (item.count / maxValue) * chartHeight;
        const x = padding + i * (barWidth + gap) + gap / 2;
        const y = height - padding - barHeight;

        const grad = ctx.createLinearGradient(0, y, 0, height - padding);
        grad.addColorStop(0, '#5865f2');
        grad.addColorStop(1, '#3a4399');

        ctx.fillStyle = grad;
        ctx.fillRect(x, y, barWidth, barHeight);

        ctx.fillStyle = '#e6e8ec';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(item.count, x + barWidth / 2, y - 5);

        ctx.fillStyle = '#8a92a6';
        ctx.fillText(item.date, x + barWidth / 2, height - padding + 18);
    });
};

let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        if (window.chartData && window.renderGamesChart) {
            window.renderGamesChart(window.chartData);
        }
    }, 200);
});