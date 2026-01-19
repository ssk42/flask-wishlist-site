"""Human-like behavior simulation for stealth browsing."""
import asyncio
import random
from typing import List, Tuple

# Amazon cookie accept button selectors
COOKIE_ACCEPT_SELECTORS = [
    "#sp-cc-accept",
    "[data-cel-widget='sp-cc-accept']",
    "input[data-action-type='DISMISS']",
    "#sp-cc-rejectall-link",  # Sometimes we need to reject tracking
]


def human_delay(base_ms: int, variance: float = 0.3) -> float:
    """Generate human-like delay with variance.

    Args:
        base_ms: Base delay in milliseconds
        variance: Variance as percentage (0.3 = +/- 30%)

    Returns:
        Delay in seconds (not milliseconds)
    """
    min_ms = base_ms * (1 - variance)
    max_ms = base_ms * (1 + variance)
    delay_ms = random.uniform(min_ms, max_ms)
    return delay_ms / 1000


def generate_bezier_points(
    start: Tuple[float, float],
    end: Tuple[float, float],
    num_points: int = 20,
    noise: float = 10.0
) -> List[Tuple[float, float]]:
    """Generate points along a bezier curve for natural mouse movement.

    Args:
        start: Starting (x, y) coordinates
        end: Ending (x, y) coordinates
        num_points: Number of points to generate
        noise: Random noise to add to control points

    Returns:
        List of (x, y) coordinates along the curve
    """
    # Generate random control points for bezier curve
    mid_x = (start[0] + end[0]) / 2 + random.uniform(-noise * 3, noise * 3)
    mid_y = (start[1] + end[1]) / 2 + random.uniform(-noise * 3, noise * 3)

    # Control points for quadratic bezier
    control = (mid_x, mid_y)

    points = []
    for i in range(num_points):
        t = i / (num_points - 1)

        # Quadratic bezier formula
        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t ** 2 * end[0]
        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t ** 2 * end[1]

        # Add small noise except for start point
        if i > 0 and i < num_points - 1:
            x += random.uniform(-noise / 2, noise / 2)
            y += random.uniform(-noise / 2, noise / 2)

        points.append((x, y))

    # Ensure exact start point
    points[0] = start

    return points


async def human_mouse_move(page, target_x: float, target_y: float):
    """Move mouse in a natural curve to target position.

    Args:
        page: Playwright page object
        target_x: Target X coordinate
        target_y: Target Y coordinate
    """
    # Get current mouse position (approximate from viewport center if unknown)
    try:
        current = await page.evaluate("({x: window._mouseX || 640, y: window._mouseY || 400})")
        start = (current['x'], current['y'])
    except Exception:
        start = (640, 400)  # Default to viewport center

    # Generate curved path
    points = generate_bezier_points(start, (target_x, target_y), num_points=random.randint(15, 25))

    # Move through points
    for x, y in points:
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.005, 0.025))

    # Track position for next move
    await page.evaluate(f"window._mouseX = {target_x}; window._mouseY = {target_y}")


async def human_scroll(page, scroll_amount: int = None):
    """Scroll page in a human-like manner.

    Args:
        page: Playwright page object
        scroll_amount: Total amount to scroll (random if None)
    """
    if scroll_amount is None:
        scroll_amount = random.randint(300, 600)

    scrolled = 0
    while scrolled < scroll_amount:
        # Variable scroll chunk
        chunk = random.randint(50, 150)
        await page.mouse.wheel(0, chunk)
        scrolled += chunk

        # Random pause
        await asyncio.sleep(human_delay(300, 0.5))

        # Occasionally scroll back slightly (5% chance)
        if random.random() < 0.05:
            back = random.randint(20, 50)
            await page.mouse.wheel(0, -back)
            await asyncio.sleep(human_delay(200, 0.3))


async def handle_cookie_banner(page) -> bool:
    """Attempt to accept/dismiss cookie banner.

    Args:
        page: Playwright page object

    Returns:
        True if banner was handled, False otherwise
    """
    for selector in COOKIE_ACCEPT_SELECTORS:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                # Wait a bit like a human would
                await asyncio.sleep(human_delay(500, 0.3))
                await elem.click()
                await asyncio.sleep(human_delay(300, 0.2))
                return True
        except Exception:
            continue
    return False


async def interact_like_human(page):
    """Simulate human browsing behavior before extracting data.

    Args:
        page: Playwright page object
    """
    # 1. Wait after page load (reading time)
    await asyncio.sleep(human_delay(1000, 0.4))

    # 2. Handle cookie banner if present
    await handle_cookie_banner(page)

    # 3. Move mouse to neutral area
    viewport = page.viewport_size or {"width": 1280, "height": 800}
    await human_mouse_move(
        page,
        random.randint(int(viewport["width"] * 0.3), int(viewport["width"] * 0.7)),
        random.randint(int(viewport["height"] * 0.2), int(viewport["height"] * 0.4))
    )

    # 4. Scroll down to product area
    await human_scroll(page, random.randint(200, 400))

    # 5. Move mouse near price area (common Amazon layout)
    await human_mouse_move(
        page,
        random.randint(300, 500),
        random.randint(300, 500)
    )

    # 6. Brief pause before extraction
    await asyncio.sleep(human_delay(500, 0.3))
