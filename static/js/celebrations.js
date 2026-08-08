/**
 * Celebration effects for wishlist actions
 * Provides confetti, pulse, and glow effects for purchase/claim actions
 */
(function() {
    'use strict';

    // Colors match the Warm Plum & Gold palette
    const CONFETTI_COLORS = [
        '#7c3aed', // Primary plum
        '#a78bfa', // Light plum
        '#ec4899', // Secondary rose
        '#f472b6', // Light rose
        '#f59e0b', // Accent gold
        '#fbbf24', // Bright gold
        '#10b981'  // Success green
    ];

    const CONFETTI_COUNT = 50;

    /**
     * Create and trigger confetti explosion
     * @param {number} originX - X position as fraction of viewport (0-1)
     * @param {number} originY - Y position as fraction of viewport (0-1)
     */
    function triggerConfetti(originX = 0.5, originY = 0.5) {
        // Check for reduced motion preference
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }

        const container = document.createElement('div');
        container.className = 'confetti-container';
        document.body.appendChild(container);

        for (let i = 0; i < CONFETTI_COUNT; i++) {
            createConfettiPiece(container, originX, originY);
        }

        // Clean up after animation
        setTimeout(() => {
            container.remove();
        }, 4000);
    }

    /**
     * Create a single confetti piece
     */
    function createConfettiPiece(container, originX, originY) {
        const confetti = document.createElement('div');
        const shapes = ['confetti--circle', 'confetti--square', 'confetti--triangle'];
        const shape = shapes[Math.floor(Math.random() * shapes.length)];

        confetti.className = `confetti ${shape}`;

        // Random properties
        const color = CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)];
        const size = Math.random() * 8 + 6; // 6-14px
        const startX = (originX * window.innerWidth) + (Math.random() - 0.5) * 200;
        const drift = (Math.random() - 0.5) * 400;
        const delay = Math.random() * 0.5;
        const duration = Math.random() * 1 + 2.5; // 2.5-3.5s

        confetti.style.cssText = `
            left: ${startX}px;
            top: ${originY * window.innerHeight - 50}px;
            width: ${size}px;
            height: ${size}px;
            background-color: ${color};
            color: ${color};
            animation-delay: ${delay}s;
            animation-duration: ${duration}s;
            --confetti-drift: ${drift}px;
        `;

        container.appendChild(confetti);

        // Trigger animation
        requestAnimationFrame(() => {
            confetti.classList.add('confetti--animation');
        });
    }

    /**
     * Pulse effect on an element
     * @param {HTMLElement} element - Element to pulse
     */
    function triggerSuccessPulse(element) {
        if (!element) return;
        element.classList.add('btn-success-pulse');
        setTimeout(() => {
            element.classList.remove('btn-success-pulse');
        }, 600);
    }

    /**
     * Card celebration glow
     * @param {HTMLElement} cardElement - Card element to glow
     */
    function triggerCardCelebration(cardElement) {
        if (!cardElement) return;
        cardElement.classList.add('card-celebrating');
        setTimeout(() => {
            cardElement.classList.remove('card-celebrating');
        }, 1000);
    }

    /**
     * Status change animation
     * @param {HTMLElement} element - Element that changed status
     */
    function triggerStatusChange(element) {
        if (!element) return;
        element.classList.add('status-changed');
        setTimeout(() => {
            element.classList.remove('status-changed');
        }, 300);
    }

    // Listen for HTMX events to trigger celebrations
    document.body.addEventListener('htmx:afterSwap', function(event) {
        const target = event.detail.target;
        const xhr = event.detail.xhr;

        if (!xhr || !xhr.responseURL) return;

        const url = xhr.responseURL;

        // Trigger confetti for purchase actions
        if (url.includes('mark_purchased')) {
            const card = target.closest('.glass-card') || target;
            const rect = card.getBoundingClientRect();
            const originX = (rect.left + rect.width / 2) / window.innerWidth;
            const originY = (rect.top + rect.height / 2) / window.innerHeight;

            triggerConfetti(originX, originY);
            triggerCardCelebration(card);
        }

        // Pulse for claim actions
        if (url.includes('/claim')) {
            const card = target.closest('.glass-card') || target;
            triggerCardCelebration(card);

            const btn = target.querySelector('.btn-success, .btn-primary');
            if (btn) triggerSuccessPulse(btn);
        }

        // Status change animation for any status badge update
        const statusBadge = target.querySelector('.badge');
        if (statusBadge) {
            triggerStatusChange(statusBadge);
        }
    });

    // Expose API for manual triggering
    window.WishlistCelebrations = {
        confetti: triggerConfetti,
        pulse: triggerSuccessPulse,
        cardGlow: triggerCardCelebration,
        statusChange: triggerStatusChange
    };

    console.log('Wishlist Celebrations loaded');
})();
