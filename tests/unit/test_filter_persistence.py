"""
Tests for filter persistence functionality.
Ensures that filters are saved to session and persist across user actions.
"""

import pytest
from app import db, User, Item, STATUS_CHOICES, PRIORITY_CHOICES


def login_via_post(client, email):
    """Helper to login via POST request."""
    return client.post("/login", data={"email": email}, follow_redirects=True)


class TestFilterPersistence:
    """Test filter persistence across user sessions and actions."""

    def test_filters_saved_to_session_when_applied(self, client, app, login, user, other_user):
        """Test that filters are saved to session when applied."""
        with app.app_context():
            # Create test items
            db.session.add_all([
                Item(
                    description="High Priority Item",
                    status="Available",
                    priority="High",
                    category="Electronics",
                    user_id=user,
                ),
                Item(
                    description="Medium Priority Item",
                    status="Claimed",
                    priority="Medium",
                    category="Books",
                    user_id=other_user,
                ),
            ])
            db.session.commit()

        # Apply filters
        response = client.get("/items", query_string={
            "user_filter": user,
            "status_filter": "Available",
            "priority_filter": "High",
            "category_filter": "Electronics",
            "q": "Priority",
            "sort_by": "price",
            "sort_order": "desc"
        })

        assert response.status_code == 200
        
        # Check that filters are in session
        with client.session_transaction() as session:
            assert session.get('user_filter') == user
            assert session.get('status_filter') == "Available"
            assert session.get('priority_filter') == "High"
            assert session.get('category_filter') == "Electronics"
            assert session.get('q') == "Priority"
            assert session.get('sort_by') == "price"
            assert session.get('sort_order') == "desc"

    def test_filters_retrieved_from_session_when_no_new_filters(self, client, app, login, user, other_user):
        """Test that filters are retrieved from session when no new filters provided."""
        with app.app_context():
            # Create test items
            db.session.add_all([
                Item(
                    description="Session Filter Item",
                    status="Available",
                    priority="High",
                    user_id=user,
                ),
                Item(
                    description="Should Be Hidden",
                    status="Claimed",
                    priority="Low",
                    user_id=other_user,
                ),
            ])
            db.session.commit()

        # First, set filters in session
        with client.session_transaction() as session:
            session['user_filter'] = user
            session['status_filter'] = "Available"
            session['priority_filter'] = "High"

        # Then access items without providing filters
        response = client.get("/items")

        assert response.status_code == 200
        assert b"Session Filter Item" in response.data
        assert b"Should Be Hidden" not in response.data

    def test_filters_persist_after_submit_item(self, client, app, login, user):
        """Test that filters persist after submitting a new item."""
        with app.app_context():
            # Create initial item
            db.session.add(
                Item(
                    description="Existing Item",
                    status="Available",
                    priority="High",
                    user_id=user,
                )
            )
            db.session.commit()

        # Set filters in session
        with client.session_transaction() as session:
            session['status_filter'] = "Available"
            session['priority_filter'] = "High"

        # Submit new item
        response = client.post(
            "/submit_item",
            data={
                "description": "New Item",
                "status": "Available",
                "priority": "High",
                "price": "99.99",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"New Item" in response.data
        
        # Check that filters are still in session
        with client.session_transaction() as session:
            assert session.get('status_filter') == "Available"
            assert session.get('priority_filter') == "High"

    def test_filters_persist_after_edit_item(self, client, app, login, user):
        """Test that filters persist after editing an item."""
        with app.app_context():
            item = Item(
                description="Original Description",
                status="Available",
                priority="High",
                user_id=user,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Set filters in session
        with client.session_transaction() as session:
            session['status_filter'] = "Available"

        # Edit the item
        response = client.post(
            f"/edit_item/{item_id}",
            data={
                "description": "Updated Description",
                "status": "Available",
                "priority": "High",
                "price": "50.00",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Updated Description" in response.data
        
        # Check that filters are still in session
        with client.session_transaction() as session:
            assert session.get('status_filter') == "Available"

    def test_filters_persist_after_claim_item(self, client, app, login, user, other_user):
        """Test that filters persist after claiming an item."""
        with app.app_context():
            item = Item(
                description="Claimable Item",
                status="Available",
                priority="High",
                user_id=user,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Login as other user and set filters
        login_via_post(client, "other@example.com")
        with client.session_transaction() as session:
            session['user_filter'] = user
            session['status_filter'] = "Available"

        # Claim the item
        response = client.post(f"/claim_item/{item_id}", follow_redirects=True)

        assert response.status_code == 200
        assert b"You have claimed" in response.data
        
        # Check that filters are still in session
        with client.session_transaction() as session:
            assert session.get('user_filter') == user
            assert session.get('status_filter') == "Available"

    def test_filters_persist_after_delete_item(self, client, app, login, user):
        """Test that filters persist after deleting an item."""
        with app.app_context():
            item = Item(
                description="Deletable Item",
                status="Available",
                priority="High",
                user_id=user,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        # Set filters in session
        with client.session_transaction() as session:
            session['status_filter'] = "Available"
            session['priority_filter'] = "High"

        # Delete the item
        response = client.get(f"/delete_item/{item_id}", follow_redirects=True)

        assert response.status_code == 200
        assert b"Item deleted" in response.data
        
        # Check that filters are still in session
        with client.session_transaction() as session:
            assert session.get('status_filter') == "Available"
            assert session.get('priority_filter') == "High"

    def test_clear_filters_removes_session_filters(self, client, app, login, user):
        """Test that clear_filters parameter removes all filters from session."""
        # Set filters in session
        with client.session_transaction() as session:
            session['user_filter'] = user
            session['status_filter'] = "Available"
            session['priority_filter'] = "High"
            session['category_filter'] = "Electronics"
            session['q'] = "test"
            session['sort_by'] = "price"
            session['sort_order'] = "desc"

        # Clear filters
        response = client.get("/items", query_string={"clear_filters": "true"}, follow_redirects=True)

        assert response.status_code == 200
        
        # Check that filters are removed from session
        with client.session_transaction() as session:
            assert session.get('user_filter') is None
            assert session.get('status_filter') is None
            assert session.get('priority_filter') is None
            assert session.get('category_filter') is None
            assert session.get('q') is None
            assert session.get('sort_by') is None
            assert session.get('sort_order') is None

    def test_new_filters_override_session_filters(self, client, app, login, user, other_user):
        """Test that new filters override session filters."""
        with app.app_context():
            db.session.add_all([
                Item(
                    description="User 1 Item",
                    status="Available",
                    priority="High",
                    user_id=user,
                ),
                Item(
                    description="User 2 Item",
                    status="Available",
                    priority="High",
                    user_id=other_user,
                ),
            ])
            db.session.commit()

        # Set initial filters in session
        with client.session_transaction() as session:
            session['user_filter'] = user
            session['status_filter'] = "Available"

        # Apply new filters
        response = client.get("/items", query_string={
            "user_filter": other_user,
            "status_filter": "Claimed",
        })

        assert response.status_code == 200
        
        # Check that new filters are in session
        with client.session_transaction() as session:
            assert session.get('user_filter') == other_user
            assert session.get('status_filter') == "Claimed"

    def test_partial_filters_work_correctly(self, client, app, login, user, other_user):
        """Test that partial filters work correctly."""
        with app.app_context():
            db.session.add_all([
                Item(
                    description="High Priority Item",
                    status="Available",
                    priority="High",
                    user_id=user,
                ),
                Item(
                    description="Low Priority Item",
                    status="Available",
                    priority="Low",
                    user_id=user,
                ),
                Item(
                    description="Other User Item",
                    status="Available",
                    priority="High",
                    user_id=other_user,
                ),
            ])
            db.session.commit()

        # Apply only user filter
        response = client.get("/items", query_string={"user_filter": user})

        assert response.status_code == 200
        assert b"High Priority Item" in response.data
        assert b"Low Priority Item" in response.data
        assert b"Other User Item" not in response.data
        
        # Check that only user filter is in session
        with client.session_transaction() as session:
            assert session.get('user_filter') == user
            assert session.get('status_filter') is None
            assert session.get('priority_filter') is None

    def test_empty_string_filters_handled_correctly(self, client, app, login, user):
        """Test that empty string filters are handled correctly."""
        with app.app_context():
            db.session.add(
                Item(
                    description="Test Item",
                    status="Available",
                    priority="High",
                    category="Electronics",
                    user_id=user,
                )
            )
            db.session.commit()

        # Apply filters with empty strings
        response = client.get("/items", query_string={
            "category_filter": "",
            "q": "",
        })

        assert response.status_code == 200
        assert b"Test Item" in response.data
        
        # Check that empty strings are not saved to session
        with client.session_transaction() as session:
            assert session.get('category_filter') is None
            assert session.get('q') is None

    def test_sort_parameters_saved_to_session(self, client, app, login, user):
        """Test that sort parameters are saved to session."""
        with app.app_context():
            db.session.add_all([
                Item(
                    description="Cheap Item",
                    status="Available",
                    priority="High",
                    price=10.00,
                    user_id=user,
                ),
                Item(
                    description="Expensive Item",
                    status="Available",
                    priority="High",
                    price=100.00,
                    user_id=user,
                ),
            ])
            db.session.commit()

        # Apply sort parameters
        response = client.get("/items", query_string={
            "sort_by": "price",
            "sort_order": "desc",
        })

        assert response.status_code == 200
        
        # Check that sort parameters are in session
        with client.session_transaction() as session:
            assert session.get('sort_by') == "price"
            assert session.get('sort_order') == "desc"

    def test_filters_with_default_sorting(self, client, app, login, user):
        """Test that filters work with default sorting."""
        with app.app_context():
            db.session.add(
                Item(
                    description="Test Item",
                    status="Available",
                    priority="High",
                    user_id=user,
                )
            )
            db.session.commit()

        # Apply only filters without sort parameters
        response = client.get("/items", query_string={
            "status_filter": "Available",
        })

        assert response.status_code == 200
        assert b"Test Item" in response.data
        
        # Check that default sort parameters are used
        with client.session_transaction() as session:
            assert session.get('status_filter') == "Available"
            assert session.get('sort_by') == "priority"  # default
            assert session.get('sort_order') == "asc"    # default

    def test_get_items_url_with_filters_helper_function(self, client, app, login):
        """Test the helper function for building URLs with filters."""
        # Set filters in session
        with client.session_transaction() as session:
            session['user_filter'] = 1
            session['status_filter'] = "Available"
            session['priority_filter'] = "High"
            session['category_filter'] = "Electronics"
            session['q'] = "test"
            session['sort_by'] = "price"
            session['sort_order'] = "desc"

        # Test the helper function indirectly by checking that redirects preserve filters
        # First, create an item to test with
        response = client.post(
            "/submit_item",
            data={
                "description": "Test Item for Helper",
                "status": "Available",
                "priority": "High",
                "price": "99.99",
            },
            follow_redirects=False,
        )
        
        # The redirect should preserve the session filters
        assert response.status_code == 302
        location = response.headers.get('Location', '')
        
        # Check that the redirect URL contains the session filters
        assert "user_filter=1" in location
        assert "status_filter=Available" in location
        assert "priority_filter=High" in location
        assert "category_filter=Electronics" in location
        assert "q=test" in location
        assert "sort_by=price" in location
        assert "sort_order=desc" in location

    def test_get_items_url_with_filters_empty_session(self, client, app, login):
        """Test the helper function with empty session."""
        from app import get_items_url_with_filters
        
        # Ensure session is empty
        with client.session_transaction() as session:
            session.clear()

        # Test the helper function within a request context
        with app.test_request_context():
            url = get_items_url_with_filters()
            assert url == "/items"
            assert "?" not in url

    def test_filter_persistence_across_multiple_actions(self, client, app, login, user, other_user):
        """Test filter persistence across multiple consecutive actions."""
        with app.app_context():
            item1 = Item(
                description="Item 1",
                status="Available",
                priority="High",
                user_id=user,
            )
            item2 = Item(
                description="Item 2",
                status="Available",
                priority="High",
                user_id=user,
            )
            db.session.add_all([item1, item2])
            db.session.commit()
            item1_id = item1.id
            item2_id = item2.id

        # Set filters in session
        with client.session_transaction() as session:
            session['status_filter'] = "Available"
            session['priority_filter'] = "High"

        # Login as other user to claim item
        login_via_post(client, "other@example.com")

        # Claim first item
        response = client.post(f"/claim_item/{item1_id}", follow_redirects=True)
        assert response.status_code == 200
        assert b"You have claimed" in response.data

        # Check filters still persist
        with client.session_transaction() as session:
            assert session.get('status_filter') == "Available"
            assert session.get('priority_filter') == "High"

        # Login back as original user to edit second item
        login_via_post(client, "test@example.com")

        # Edit second item
        response = client.post(
            f"/edit_item/{item2_id}",
            data={
                "description": "Updated Item 2",
                "status": "Available",
                "priority": "High",
                "price": "99.99",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Item updated successfully" in response.data

        # Check filters still persist
        with client.session_transaction() as session:
            assert session.get('status_filter') == "Available"
            assert session.get('priority_filter') == "High"

    def test_filter_persistence_with_invalid_parameters(self, client, app, login, user):
        """Test filter persistence when invalid parameters are provided."""
        with app.app_context():
            db.session.add(
                Item(
                    description="Test Item",
                    status="Available",
                    priority="High",
                    user_id=user,
                )
            )
            db.session.commit()

        # Set valid filters in session
        with client.session_transaction() as session:
            session['status_filter'] = "Available"
            session['priority_filter'] = "High"

        # Try to access items with invalid user_filter parameter
        response = client.get("/items", query_string={"user_filter": "invalid"})

        assert response.status_code == 200
        assert b"Test Item" in response.data
        
        # Check that session filters are still intact
        with client.session_transaction() as session:
            assert session.get('status_filter') == "Available"
            assert session.get('priority_filter') == "High"
            assert session.get('user_filter') is None  # invalid parameter not saved

    def test_filter_persistence_with_whitespace_handling(self, client, app, login, user):
        """Test that whitespace in filters is handled correctly."""
        with app.app_context():
            db.session.add(
                Item(
                    description="Test Item",
                    status="Available",
                    priority="High",
                    category="Electronics",
                    user_id=user,
                )
            )
            db.session.commit()

        # Apply filters with whitespace
        response = client.get("/items", query_string={
            "category_filter": "  Electronics  ",
            "q": "  Test  ",
        })

        assert response.status_code == 200
        assert b"Test Item" in response.data
        
        # Check that whitespace is stripped
        with client.session_transaction() as session:
            assert session.get('category_filter') == "Electronics"
            assert session.get('q') == "Test"
