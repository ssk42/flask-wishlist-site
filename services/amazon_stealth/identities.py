"""Browser identity profiles for stealth extraction."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BrowserIdentity:
    """Represents a unique browser fingerprint for stealth requests."""

    id: str
    user_agent: str
    viewport: dict
    timezone: str
    locale: str
    color_scheme: str
    device_scale: float
    webgl_vendor: str
    webgl_renderer: str

    # Runtime state (not part of profile definition)
    requests_made: int = field(default=0)
    burned_until: Optional[datetime] = field(default=None)


# Pre-defined identity profiles matching real browser configurations
# fmt: off
# noqa: E501
IDENTITY_PROFILES = [
    {
        "id": "mac_chrome_1",
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1440, "height": 900},
        "timezone": "America/New_York",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 2,
        "webgl_vendor": "Google Inc. (Apple)",
        "webgl_renderer": "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)",
    },
    {
        "id": "mac_chrome_2",
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1680, "height": 1050},
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "color_scheme": "dark",
        "device_scale": 2,
        "webgl_vendor": "Google Inc. (Apple)",
        "webgl_renderer": "ANGLE (Apple, Apple M2, OpenGL 4.1)",
    },
    {
        "id": "mac_safari_1",
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.2 Safari/605.1.15"
        ),
        "viewport": {"width": 1440, "height": 900},
        "timezone": "America/Chicago",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 2,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple M1",
    },
    {
        "id": "windows_chrome_1",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1920, "height": 1080},
        "timezone": "America/New_York",
        "locale": "en-US",
        "color_scheme": "dark",
        "device_scale": 1,
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderer": (
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070, OpenGL 4.5)"
        ),
    },
    {
        "id": "windows_chrome_2",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 2560, "height": 1440},
        "timezone": "America/Denver",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 1,
        "webgl_vendor": "Google Inc. (AMD)",
        "webgl_renderer": (
            "ANGLE (AMD, AMD Radeon RX 6800 XT, OpenGL 4.6)"
        ),
    },
    {
        "id": "windows_edge_1",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
        ),
        "viewport": {"width": 1920, "height": 1080},
        "timezone": "America/Chicago",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 1.25,
        "webgl_vendor": "Google Inc. (Intel)",
        "webgl_renderer": (
            "ANGLE (Intel, Intel(R) UHD Graphics 630, OpenGL 4.6)"
        ),
    },
    {
        "id": "windows_firefox_1",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) "
            "Gecko/20100101 Firefox/122.0"
        ),
        "viewport": {"width": 1920, "height": 1080},
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "color_scheme": "dark",
        "device_scale": 1,
        "webgl_vendor": "NVIDIA Corporation",
        "webgl_renderer": "NVIDIA GeForce GTX 1660/PCIe/SSE2",
    },
    {
        "id": "linux_chrome_1",
        "user_agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1920, "height": 1080},
        "timezone": "America/New_York",
        "locale": "en-US",
        "color_scheme": "dark",
        "device_scale": 1,
        "webgl_vendor": "Google Inc. (NVIDIA Corporation)",
        "webgl_renderer": (
            "ANGLE (NVIDIA Corporation, NVIDIA GeForce RTX 2080/"
            "PCIe/SSE2, OpenGL 4.5)"
        ),
    },
    {
        "id": "linux_firefox_1",
        "user_agent": (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) "
            "Gecko/20100101 Firefox/122.0"
        ),
        "viewport": {"width": 1920, "height": 1080},
        "timezone": "America/Chicago",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 1,
        "webgl_vendor": "AMD",
        "webgl_renderer": (
            "AMD Radeon RX 580 Series (polaris10, LLVM 15.0.7, "
            "DRM 3.49, 6.2.0-39-generic)"
        ),
    },
    {
        "id": "mac_chrome_3",
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1512, "height": 982},
        "timezone": "America/Phoenix",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 2,
        "webgl_vendor": "Google Inc. (Apple)",
        "webgl_renderer": "ANGLE (Apple, Apple M3 Max, OpenGL 4.1)",
    },
    {
        "id": "windows_chrome_3",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1366, "height": 768},
        "timezone": "America/New_York",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 1,
        "webgl_vendor": "Google Inc. (Intel)",
        "webgl_renderer": (
            "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics, OpenGL 4.6)"
        ),
    },
    {
        "id": "mac_safari_2",
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.6 Safari/605.1.15"
        ),
        "viewport": {"width": 1280, "height": 800},
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "color_scheme": "dark",
        "device_scale": 2,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple M2 Pro",
    },
]
# fmt: on
