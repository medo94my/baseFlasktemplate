import pytest
from app.modules.models import User, load_user
from app import db as DBASE # Use the db fixture from conftest.py via DBASE alias
from werkzeug.security import check_password_hash

def test_create_user(db): # db fixture is injected
    """
    Test creating a User instance and saving it to the in-memory database.
    Verify attributes.
    """
    assert User.query.count() == 0
    user = User(
        name="Test User",
        email="test@example.com",
        # Storing pre-hashed password directly for this model test.
        # Password hashing logic is typically in forms or controller logic during registration.
        password="hashed_password", 
        role=1,
        status=1,
        profile_image="default.png"
    )
    DBASE.session.add(user)
    DBASE.session.commit()

    assert User.query.count() == 1
    retrieved_user = User.query.first()
    assert retrieved_user is not None
    assert retrieved_user.name == "Test User"
    assert retrieved_user.email == "test@example.com"
    assert retrieved_user.password == "hashed_password" # Direct check, hash check is separate
    assert retrieved_user.role == 1
    assert retrieved_user.status == 1
    assert retrieved_user.profile_image == "default.png"
    assert retrieved_user.is_active is True
    assert retrieved_user.is_authenticated is True # Based on UserMixin
    assert retrieved_user.is_anonymous is False

def test_password_hashing_implicit(db):
    """
    Test that the password attribute of a User object stores the value it's given.
    This test is not about testing the hashing process itself (which happens
    elsewhere, e.g., in controller/registration logic), but rather that the User model
    correctly persists the password value it receives.
    It also implicitly shows that the model doesn't re-hash an already hashed password.
    """
    plain_password = "cat"
    # In a real scenario, registration logic would generate this hash:
    # from werkzeug.security import generate_password_hash
    # hashed_password = generate_password_hash(plain_password)
    hashed_password = "generated_hash_for_cat" # Using a placeholder for a pre-hashed value

    user = User(
        name="Hash Test",
        email="hash@example.com",
        password=hashed_password 
    )
    DBASE.session.add(user)
    DBASE.session.commit()

    retrieved_user = User.query.filter_by(email="hash@example.com").first()
    assert retrieved_user.password != plain_password
    assert retrieved_user.password == hashed_password
    # To truly test hashing, you'd call check_password_hash(retrieved_user.password, plain_password)
    # but that depends on generate_password_hash being used, which is in controller logic.

def test_user_representation(db):
    """Test User.__repr__ method."""
    user = User(name="Repr User", email="repr@example.com", password="pw")
    DBASE.session.add(user)
    DBASE.session.commit()
    
    retrieved_user = User.query.filter_by(email="repr@example.com").first()
    expected_repr = f'<User {retrieved_user.id}>' # ID is assigned after commit
    assert repr(retrieved_user) == expected_repr

def test_user_loader_valid_id(db):
    """Test the load_user function with a valid user ID."""
    user = User(name="Loader Test", email="loader@example.com", password="pw")
    DBASE.session.add(user)
    DBASE.session.commit()
    
    loaded_user = load_user(str(user.id)) # load_user expects string ID
    assert loaded_user is not None
    assert loaded_user.id == user.id
    assert loaded_user.email == "loader@example.com"

def test_user_loader_invalid_id(db):
    """Test the load_user function with an invalid user ID."""
    loaded_user = load_user("999") # Assuming 999 doesn't exist
    assert loaded_user is None

def test_user_loader_non_integer_id(db):
    """Test the load_user function with a non-integer user ID."""
    loaded_user = load_user("abc")
    assert loaded_user is None

# Example of how you might test methods if User model had them:
# def test_user_get_profile_image_url(db):
#     user = User(name="Img Test", email="img@example.com", password="pw", profile_image="test.jpg")
#     DBASE.session.add(user)
#     DBASE.session.commit()
#     # Assuming a method like user.get_profile_image_url() that might construct a URL
#     # For this project, image URL construction is in controller/template.
#     assert user.profile_image == "test.jpg" # Direct attribute check is enough here
