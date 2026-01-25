from app import create_app
from models import db, User, Item, Contribution

app = create_app()


def seed():
    with app.app_context():
        # Create Users
        owner = User.query.filter_by(email="owner@example.com").first()
        if not owner:
            owner = User(name="Owner", email="owner@example.com")
            owner.set_password("wishlist2025")
            db.session.add(owner)
        else:
            owner.set_password("wishlist2025")

        splitter = User.query.filter_by(email="splitter@example.com").first()
        if not splitter:
            splitter = User(name="Splitter", email="splitter@example.com")
            splitter.set_password("wishlist2025")
            db.session.add(splitter)
        else:
            splitter.set_password("wishlist2025")

        contributor = User.query.filter_by(
            email="contributor@example.com").first()
        if not contributor:
            contributor = User(
                name="Contributor",
                email="contributor@example.com")
            contributor.set_password("wishlist2025")
            db.session.add(contributor)
        else:
            contributor.set_password("wishlist2025")

        db.session.commit()

        # Create/Find Item
        item = Item.query.filter_by(description="Browser Test Gift").first()
        if not item:
            item = Item(
                description="Browser Test Gift",
                price=100.0,
                user_id=owner.id,
                status="Splitting"
            )
            db.session.add(item)
            db.session.commit()

            # Create Initial Contribution
            contrib = Contribution(
                item_id=item.id,
                user_id=splitter.id,
                amount=25.0,
                is_organizer=True
            )
            db.session.add(contrib)
            db.session.commit()
            print(f"Created item {item.id} in Splitting status")
        else:
            print(f"Item {item.id} already exists")
            # Reset status if needed
            if item.status != 'Splitting':
                item.status = 'Splitting'
            db.session.commit()

            # Ensure contribution exists
            contrib = Contribution.query.filter_by(
                item_id=item.id, user_id=splitter.id).first()
            if not contrib:
                contrib = Contribution(
                    item_id=item.id,
                    user_id=splitter.id,
                    amount=25.0,
                    is_organizer=True
                )
                db.session.add(contrib)
                db.session.commit()


if __name__ == "__main__":
    seed()
