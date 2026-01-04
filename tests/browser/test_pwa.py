import pytest
from playwright.sync_api import Page, expect

def test_manifest_reachable(page: Page, live_server):
    response = page.request.get(f"{live_server}/static/manifest.json")
    expect(response).to_be_ok()
    data = response.json()
    assert data["name"] == "Family Wishlist"
    assert len(data["icons"]) >= 2
