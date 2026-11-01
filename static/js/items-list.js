// Items list behavior: expand the card while its comments section is
// open. External because the production CSP blocks inline script
// (@spec GIV-CLM-021).
document.addEventListener('DOMContentLoaded', function () {
    // Handle comment collapse events to expand card height
    const collapses = document.querySelectorAll('.collapse');
    collapses.forEach(collapse => {
        collapse.addEventListener('show.bs.collapse', function () {
            const card = this.closest('.glass-card.compact');
            if (card) {
                card.classList.add('expanded');
            }
        });

        collapse.addEventListener('hide.bs.collapse', function () {
            const card = this.closest('.glass-card.compact');
            if (card) {
                card.classList.remove('expanded');
            }
        });
    });
});
