// Price history sparkline functionality
document.addEventListener('DOMContentLoaded', () => {
    initSparklines();

    // Re-initialize on HTMX swaps
    document.body.addEventListener('htmx:afterSwap', function (evt) {
        initSparklines(evt.detail.target);
    });
});

function initSparklines(container = document) {
    container.querySelectorAll('.price-sparkline').forEach(el => {
        // Skip if already initialized or no item ID
        if (el.dataset.initialized || !el.dataset.itemId) return;

        el.dataset.initialized = 'true';
        const itemId = el.dataset.itemId;

        fetch(`/api/items/${itemId}/price-history`)
            .then(res => {
                if (!res.ok) throw new Error('Fetch failed');
                return res.json();
            })
            .then(data => {
                const history = data.history;
                if (!history || history.length < 2) return; // Need at least 2 points

                // Show container
                el.style.display = 'block';
                el.title = `Price range: $${data.stats.min.toFixed(2)} - $${data.stats.max.toFixed(2)} (via ${history.length} points)`;

                const canvas = el.querySelector('canvas');
                if (!canvas) return;

                drawSparkline(canvas, history.map(h => h.price));
            })
            .catch(err => console.debug('No history or error for', itemId)); // Fail silently
    });
}

function drawSparkline(canvas, prices) {
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1; // Avoid division by zero

    // Style
    const isUp = prices[prices.length - 1] >= prices[0];
    ctx.strokeStyle = isUp ? '#dc3545' : '#28a745'; // Green if down (good), Red if up (bad) - wait, lower is better for shopping
    // Actually, Green = price went DOWN (good), Red = price went UP (bad)
    ctx.lineWidth = 1.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    ctx.beginPath();

    // Add 2px padding top/bottom
    const padding = 2;
    const effectiveHeight = height - (padding * 2);

    prices.forEach((price, i) => {
        const x = (i / (prices.length - 1)) * width;
        // Invert Y because canvas 0 is top
        const normalizedY = (price - min) / range;
        const y = height - padding - (normalizedY * effectiveHeight);

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // Add dot at end
    const lastPrice = prices[prices.length - 1];
    const lastX = width - 1.5;
    const lastY = height - padding - (((lastPrice - min) / range) * effectiveHeight);

    ctx.fillStyle = ctx.strokeStyle;
    ctx.beginPath();
    ctx.arc(lastX, lastY, 2, 0, Math.PI * 2);
    ctx.fill();
}
