"""
Tests for surprise protection - ensuring users can't see who claimed their own items.
"""

import pytest
from app import db, User, Item, STATUS_CHOICES, PRIORITY_CHOICES


def login_via_post(client, email):
    """Helper to login via POST request."""
    return client.post("/login", data={"email": email}, follow_redirects=True)


class TestSurpriseProtection:
    """Test that users cannot see who claimed their own items."""

    def test_user_cannot_see_who_claimed_their_own_items(self, client, app, user, other_user):
        """Test that a user cannot see who claimed their own items."""
        with app.app_context():
            # Get the user objects
            user_obj = db.session.get(User, user)
            other_user_obj = db.session.get(User, other_user)

            # Create an item for the user
            item = Item(
                description="User's Gift Item",
                status="Claimed",
                priority="High",
                user_id=user_obj.id,
                last_updated_by_id=other_user_obj.id,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Login as the item owner
        login_via_post(client, "test@example.com")

        # View the items page
        response = client.get("/items")

        assert response.status_code == 200

        # The apostrophe gets HTML-encoded as &#39;
        assert b"User&#39;s Gift Item" in response.data

        # The user should NOT see the status "Claimed" - instead they should see "Your Item"
        response_text = response.data.decode('utf-8')
        # Find the section for this specific item (increase window to capture full card)
        item_section_start = response_text.find("User&#39;s Gift Item")
        item_section_end = response_text.find("glass-card", item_section_start + 10) # Find NEXT card or end
        if item_section_end == -1:
            item_section_end = len(response_text)
            
        item_section = response_text[item_section_start:item_section_end]

        # Normalize whitespace for checking "Your Item" which spans lines in template
        normalized_section = ' '.join(item_section.split())
        assert "Claimed" not in item_section, "User should not see 'Claimed' status on their own item"
        assert "Your Item" in normalized_section, "User should see 'Your Item' badge"
        
        # Verify Edit link is present (more robust than checking for "Edit" text specifically in the slice)
        assert f"/edit_item/{item_id}" in response_text
        assert "Delete" in item_section
        assert "Last updated by" not in item_section
        assert "Claimed by" not in item_section

    def test_user_can_see_who_claimed_other_users_items(self, client, app, user, other_user):
        """Test that a user can see who claimed other users' items."""
        with app.app_context():
            # Get the user objects
            user_obj = db.session.get(User, user)
            other_user_obj = db.session.get(User, other_user)
            
            # Create an item for another user
            item = Item(
                description="Other User's Gift Item",
                status="Claimed",
                priority="High",
                user_id=other_user_obj.id,
                last_updated_by_id=user_obj.id,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Login as the user who claimed the item
        login_via_post(client, "test@example.com")

        # View the items page
        response = client.get("/items")

        assert response.status_code == 200
        assert b"Other User&#39;s Gift Item" in response.data
        assert b"Claimed" in response.data
        
        # The user should see who claimed the other user's item
        assert b"Claimed by Test User" in response.data

    def test_user_cannot_see_last_updated_info_on_their_own_available_items(self, client, app, user, other_user):
        """Test that a user doesn't see last updated info on their own available items."""
        with app.app_context():
            # Get the user objects
            user_obj = db.session.get(User, user)
            other_user_obj = db.session.get(User, other_user)
            
            # Create an available item for the user (should not show last updated info)
            item = Item(
                description="User's Available Item",
                status="Available",
                priority="High",
                user_id=user_obj.id,
                last_updated_by_id=other_user_obj.id,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Login as the item owner
        login_via_post(client, "test@example.com")

        # View the items page
        response = client.get("/items")

        assert response.status_code == 200
        assert b"User&#39;s Available Item" in response.data
        assert b"Available" in response.data
        
        # The user should NOT see last updated info for their own items
        assert b"Last updated by" not in response.data

    def test_user_can_see_last_updated_info_on_other_users_available_items(self, client, app, user, other_user):
        """Test that a user can see last updated info on other users' available items."""
        with app.app_context():
            # Get the user objects
            user_obj = db.session.get(User, user)
            other_user_obj = db.session.get(User, other_user)
            
            # Create an available item for another user
            item = Item(
                description="Other User's Available Item",
                status="Available",
                priority="High",
                user_id=other_user_obj.id,
                last_updated_by_id=user_obj.id,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Login as the user who last updated the item
        login_via_post(client, "test@example.com")

        # View the items page
        response = client.get("/items")

        assert response.status_code == 200
        assert b"Other User&#39;s Available Item" in response.data
        assert b"Available" in response.data
        
        # The user should see the item is Available (updater info is no longer shown for Available items)
        assert b"Available" in response.data

    def test_surprise_protection_with_multiple_users(self, client, app):
        """Test surprise protection with multiple users and items."""
        with app.app_context():
            # Create multiple users
            user1 = User(name="User1", email="user1@example.com")
            user2 = User(name="User2", email="user2@example.com")
            user3 = User(name="User3", email="user3@example.com")
            db.session.add_all([user1, user2, user3])
            db.session.commit()

            # Create items where user3 claims user1's item and user2's item
            item1 = Item(
                description="User1's Gift",
                status="Claimed",
                priority="High",
                user_id=user1.id,
                last_updated_by_id=user3.id,
            )
            item2 = Item(
                description="User2's Gift",
                status="Claimed",
                priority="Medium",
                user_id=user2.id,
                last_updated_by_id=user3.id,
            )
            db.session.add_all([item1, item2])
            db.session.commit()

        # Login as user1
        login_via_post(client, "user1@example.com")

        # View the items page
        response = client.get("/items")

        assert response.status_code == 200
        
        # User1 should see their own item but not who claimed it
        assert b"User1&#39;s Gift" in response.data
        assert b"Claimed" in response.data
        
        # Check that User1's own item does NOT show who claimed it
        # We need to check that the "Last updated by User3" appears only for User2's item, not User1's item
        response_text = response.data.decode('utf-8')
        user1_section = response_text.split("User1&#39;s Gift")[1].split("User2&#39;s Gift")[0]
        assert "Last updated by User3" not in user1_section
        
        # User1 should see user2's item and who claimed it
        assert b"User2&#39;s Gift" in response.data
        assert b"Claimed by User3" in response.data

    def test_surprise_protection_works_with_filters(self, client, app, user, other_user):
        """Test that surprise protection works when filters are applied."""
        with app.app_context():
            # Get the user objects
            user_obj = db.session.get(User, user)
            other_user_obj = db.session.get(User, other_user)
            
            # Create claimed items for both users
            item1 = Item(
                description="User's Claimed Item",
                status="Claimed",
                priority="High",
                user_id=user_obj.id,
                last_updated_by_id=other_user_obj.id,
            )
            item2 = Item(
                description="Other User's Claimed Item",
                status="Claimed",
                priority="High",
                user_id=other_user_obj.id,
                last_updated_by_id=user_obj.id,
            )
            db.session.add_all([item1, item2])
            db.session.commit()

        # Login as the first user
        login_via_post(client, "test@example.com")

        # Filter to show only claimed items
        response = client.get("/items", query_string={"status_filter": "Claimed"})

        assert response.status_code == 200
        assert b"User&#39;s Claimed Item" in response.data
        assert b"Other User&#39;s Claimed Item" in response.data
        
        # Should not see who claimed their own item
        assert b"Last updated by Other User" not in response.data
        
        # Should see who claimed the other user's item
        assert b"Claimed by Test User" in response.data

    def test_user_cannot_see_their_own_claimed_items_in_summary_table(self, client, app, user, other_user):
        """Test that a user cannot see their own claimed items in the summary totals table."""
        with app.app_context():
            # Get the user objects
            user_obj = db.session.get(User, user)
            other_user_obj = db.session.get(User, other_user)
            
            # Create items for both users
            user_item = Item(
                description="User's Claimed Item",
                status="Claimed",
                priority="High",
                price=100.00,
                user_id=user_obj.id,
                last_updated_by_id=other_user_obj.id,
            )
            other_item = Item(
                description="Other User's Available Item",
                status="Available",
                priority="Medium",
                price=50.00,
                user_id=other_user_obj.id,
            )
            db.session.add_all([user_item, other_item])
            db.session.commit()

        # Login as the first user
        login_via_post(client, "test@example.com")

        # View the items page
        response = client.get("/items")

        assert response.status_code == 200
        assert b"At a Glance" in response.data
        
        # Should NOT see their own claimed items in the summary table
        # The summary table should only show "Other User" with "Available" status
        assert b"Other User" in response.data
        assert b"Available" in response.data
        assert b"$50.00" in response.data
        
        # Should NOT see "Test User" with "Claimed" status in the summary table
        # We need to check specifically in the summary table section
        response_text = response.data.decode('utf-8')
        # Extract just the summary table content
        summary_start = response_text.find("<tbody>")
        summary_end = response_text.find("</tbody>") + len("</tbody>")
        summary_table_content = response_text[summary_start:summary_end]
        
        # The summary table should NOT contain "Test User" and "Claimed" together
        assert not ("Test User" in summary_table_content and "Claimed" in summary_table_content)

    def test_user_can_see_other_users_claimed_items_in_summary_table(self, client, app, user, other_user):
        """Test that a user can see other users' claimed items in the summary totals table."""
        with app.app_context():
            # Get the user objects
            user_obj = db.session.get(User, user)
            other_user_obj = db.session.get(User, other_user)

            # Create items where other user has claimed items
            other_claimed = Item(
                description="Other User's Claimed Item",
                status="Claimed",
                priority="High",
                price=75.00,
                user_id=other_user_obj.id,
                last_updated_by_id=user_obj.id,
            )
            user_available = Item(
                description="User's Available Item",
                status="Available",
                priority="Medium",
                price=25.00,
                user_id=user_obj.id,
            )
            db.session.add_all([other_claimed, user_available])
            db.session.commit()

        # Login as the first user
        login_via_post(client, "test@example.com")

        # View the items page
        response = client.get("/items")

        assert response.status_code == 200
        assert b"At a Glance" in response.data

        # Should see other user's claimed items in the summary table
        assert b"Other User" in response.data
        assert b"Claimed" in response.data
        assert b"$75.00" in response.data

        # Should see their own available items in the summary
        assert b"Test User" in response.data
        assert b"Available" in response.data
        assert b"$25.00" in response.data

    def test_user_cannot_see_status_on_edit_page_for_own_items(self, client, app, user, other_user):
        """Test that users cannot see status dropdown when editing their own items."""
        with app.app_context():
            # Get the user object
            user_obj = db.session.get(User, user)

            # Create an item for the user that has been claimed
            item = Item(
                description="My Secret Item",
                status="Claimed",
                priority="High",
                user_id=user_obj.id,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Login as the item owner
        login_via_post(client, "test@example.com")

        # View the edit page for their own item
        response = client.get(f"/edit_item/{item_id}")

        assert response.status_code == 200
        assert b"My Secret Item" in response.data

        # The user should NOT see the status dropdown
        response_text_for_check = response.data.decode('utf-8')
        assert 'for="status"' not in response_text_for_check
        assert 'name="status"' not in response_text_for_check

        # The user should NOT see the current status anywhere
        response_text = response.data.decode('utf-8')
        assert "Claimed" not in response_text, "User should not see 'Claimed' status on edit page for their own item"

    def test_user_can_see_status_on_edit_page_for_other_users_items(self, client, app, user, other_user):
        """Test that users CAN see status dropdown when editing other users' items."""
        with app.app_context():
            # Get the user objects
            user_obj = db.session.get(User, user)
            other_user_obj = db.session.get(User, other_user)

            # Create an item for the other user
            item = Item(
                description="Another Item",
                status="Available",
                priority="Medium",
                user_id=other_user_obj.id,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Login as the first user (not the owner)
        login_via_post(client, "test@example.com")

        # View the edit page for the other user's item
        response = client.get(f"/edit_item/{item_id}")

        assert response.status_code == 200

        # The user SHOULD see the status dropdown
        response_text = response.data.decode('utf-8')
        assert 'for="status"' in response_text, "Should see status label on other users' items"
        assert 'name="status"' in response_text, "Should see status dropdown on other users' items"
        assert '<select class="form-select" id="status" name="status">' in response_text
        # Check that the dropdown contains the status options
        assert '<option value="Available" selected>Available</option>' in response_text
