import pytest
from flask import session, url_for, get_flashed_messages
from werkzeug.security import generate_password_hash, check_password_hash
from unittest.mock import patch, MagicMock
from app.modules.models import User
from app import db as DBASE # Use alias for clarity with fixture 'db'

# Helper function to create a user for testing
def create_test_user(db_session, name, email, password_plain, role=1, status=1):
    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password_plain), # Hash password on creation
        role=role,
        status=status
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_user(db): # Uses the db fixture from conftest.py
    """Creates a standard test user for login tests."""
    return create_test_user(DBASE.session, "Test User", "test@example.com", "password123")

@pytest.fixture
def logged_in_user(client, test_user):
    """Logs in the test_user and returns the user object."""
    # This fixture simulates a login by directly manipulating session/context
    # A more integrated way is to POST to signin, but this is faster for setup
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['_fresh'] = True # Common for Flask-Login
    # We also need to ensure flask_login.current_user is set if controllers use it directly
    # This is tricky without request context. For direct current_user access,
    # tests might need to run within a request context or current_user needs patching.
    # For now, relying on session for authentication checks.
    return test_user


# --- Authentication Tests ---

def test_signin_page_loads(client):
    """Test GET request to /auth/signin/."""
    response = client.get(url_for('auth.signin'))
    assert response.status_code == 200
    assert b"Sign In" in response.data # Check for some text from the template

@patch('app.modules.controllers.User.query')
def test_successful_signin(mock_user_query, client, test_user):
    """Test POST to /auth/signin/ with valid credentials."""
    # Configure User.query.filter_by().first() to return our test_user
    # Password was 'password123', hash is stored in test_user.password
    mock_user_query.filter_by(email=test_user.email).first.return_value = test_user
    
    # We don't need to mock check_password_hash if we use the real hash from test_user
    # and the real check_password_hash function. The test_user fixture already stores a hashed password.

    response = client.post(url_for('auth.signin'), data={
        'email': test_user.email,
        'password': 'password123' # Plain password for form submission
    }, follow_redirects=True) # follow_redirects=True to get the response from the final redirected page
    
    assert response.status_code == 200 # Successful redirect should result in a 200 OK
    # Check that the final URL is the welcome page after redirection
    assert url_for('auth.welcome') in response.request.path 
    assert b"Welcome Test User" in response.data # Check for content from the welcome template
    
    # Verify session variables set by Flask-Login upon successful authentication
    with client.session_transaction() as sess:
        assert sess.get('user_id') == str(test_user.id) # Flask-Login stores ID as string
        assert sess.get('_fresh') is True

@patch('app.modules.controllers.User.query')
def test_failed_signin_wrong_password(mock_user_query, client, test_user):
    """Test POST to /auth/signin/ with invalid password."""
    mock_user_query.filter_by(email=test_user.email).first.return_value = test_user

    response = client.post(url_for('auth.signin'), data={
        'email': test_user.email,
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert url_for('auth.signin') in response.request.path # Should stay on signin
    assert b"Login unsuccessful" in response.data # Check for flash message
    with client.session_transaction() as sess:
        assert sess.get('user_id') is None

@patch('app.modules.controllers.User.query')
def test_failed_signin_no_user(mock_user_query, client):
    """Test POST to /auth/signin/ with a non-existent user."""
    mock_user_query.filter_by(email="nouser@example.com").first.return_value = None

    response = client.post(url_for('auth.signin'), data={
        'email': 'nouser@example.com',
        'password': 'password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert url_for('auth.signin') in response.request.path
    assert b"Login unsuccessful" in response.data
    with client.session_transaction() as sess:
        assert sess.get('user_id') is None


def test_register_page_loads(client):
    """Test GET request to /auth/register/."""
    response = client.get(url_for('auth.register'))
    assert response.status_code == 200
    assert b"Register" in response.data

@patch('app.modules.controllers.db.session.add')
@patch('app.modules.controllers.db.session.commit')
def test_successful_registration(mock_db_commit, mock_db_add, client):
    """Test POST to /auth/register/ with valid data."""
    response = client.post(url_for('auth.register'), data={
        'name': 'New User',
        'email': 'new@example.com',
        'password': 'newpassword',
        'confirm': 'newpassword' # Assuming confirm field exists in form
    }, follow_redirects=True)

    assert response.status_code == 200 # Successful redirect lands on signin
    assert url_for('auth.signin') in response.request.path
    mock_db_add.assert_called_once()
    mock_db_commit.assert_called_once()
    # Check for flash message
    assert b"you are now registered and can login" in response.data


@patch('app.modules.controllers.User.query') # To simulate user already exists
@patch('app.modules.controllers.db.session.add')
def test_failed_registration_existing_user(mock_db_add, mock_user_query, client, test_user, db):
    """Test POST to /auth/register/ with an email that already exists."""
    # The registration logic in controllers.py uses a try-except for commit.
    # It doesn't explicitly check if user exists before trying to add.
    # If email is unique in DB, commit will fail.
    # Let's refine this: the form validation itself might check for uniqueness if User model has unique constraint.
    # For now, assuming db.session.commit() would raise an IntegrityError.

    # Make User.query.filter_by(email=test_user.email).first() return the existing user
    # This is more for a custom validator. The current code relies on DB integrity.
    # So, we'll let db.session.add be called, and mock commit to raise an error.
    
    with patch.object(DBASE.session, 'commit', side_effect=Exception("IntegrityError: duplicate key")):
        response = client.post(url_for('auth.register'), data={
            'name': 'Another User',
            'email': test_user.email, # Existing email
            'password': 'password123',
            'confirm': 'password123'
        }, follow_redirects=True)

    assert response.status_code == 200 # Stays on register page
    assert url_for('auth.register') in response.request.path # Or request.referrer
    assert mock_db_add.called # It will try to add
    # Check for flashed error message (actual message depends on error handler)
    flashed_messages = get_flashed_messages(with_categories=True, app=client.application)
    assert any(msg[0] == 'danger' and "IntegrityError" in msg[1] for msg in flashed_messages)


def test_logout_when_logged_in(client, logged_in_user):
    """Test GET request to /auth/logout when logged in."""
    # First, ensure user is "logged in" by the fixture
    with client.session_transaction() as sess:
        assert sess.get('user_id') is not None

    response = client.get(url_for('auth.logout'), follow_redirects=True)
    assert response.status_code == 200
    assert url_for('home') in response.request.path # Redirects to home
    
    with client.session_transaction() as sess:
        assert sess.get('user_id') is None
        assert sess.get('_fresh') is None
    
    # To check current_user.is_anonymous, we need a request context after logout
    # This is tricky to assert directly here without another request.
    # The session check is a good proxy.
    # A subsequent request to an @login_required route would confirm.

def test_logout_when_not_logged_in(client):
    """Test GET request to /auth/logout when not logged in."""
    # User is not logged in
    response = client.get(url_for('auth.logout'), follow_redirects=True)
    assert response.status_code == 200 # Should still redirect to home gracefully
    assert url_for('home') in response.request.path
    with client.session_transaction() as sess:
        assert sess.get('user_id') is None


# --- Account Management Tests ---

def test_account_page_loads_authenticated(client, logged_in_user):
    """Test GET to /auth/account when logged in."""
    response = client.get(url_for('auth.account'))
    assert response.status_code == 200
    assert bytes(logged_in_user.name, 'utf-8') in response.data
    assert bytes(logged_in_user.email, 'utf-8') in response.data

def test_account_page_redirects_unauthenticated(client):
    """Test GET to /auth/account when not logged in."""
    response = client.get(url_for('auth.account'), follow_redirects=False) # Don't follow to login page
    assert response.status_code == 302 # Redirect
    assert url_for('auth.signin') in response.location # Redirects to signin

@patch('app.modules.controllers.db.session.commit')
@patch('flask_login.utils._get_user') # Mocks current_user for the duration of this test via its backing function
def test_account_update_success(mock_flask_login_get_user, mock_db_commit, client, test_user, db):
    """Test POST to /auth/account with valid data (name, email)."""
    # Ensure that flask_login.current_user (which is a proxy) returns our test_user 
    # within the controller's context when accessed. This is crucial because the 
    # controller directly modifies attributes of `current_user`.
    mock_flask_login_get_user.return_value = test_user 
    
    # Although the logged_in_user fixture could set up the session, explicitly
    # mocking `_get_user` is more robust for ensuring `current_user` is the correct
    # object instance when the controller code executes.
    # The session still needs to be valid for @login_required to pass.
    with client.session_transaction() as sess:
        sess['user_id'] = str(test_user.id)
        sess['_fresh'] = True

    new_name = "Updated Name"
    new_email = "updated@example.com"
    response = client.post(url_for('auth.account'), data={
        'name': new_name,
        'email': new_email,
        # profile_picture is not sent, so it shouldn't be processed
    }, follow_redirects=True)

    assert response.status_code == 200
    assert url_for('auth.account') in response.request.path # Stays on account page
    assert b"Your information has been updated" in response.data
    
    mock_db_commit.assert_called_once()
    # Verify user object was changed before commit (if possible, or check DB after).
    # Since current_user might be a proxy or a different instance than test_user
    # depending on Flask-Login's internals and mocking, it's safest to re-fetch 
    # the user from the database session to check committed data.
    # DBASE.session.get(User, test_user.id) fetches the user by primary key.
    updated_user_from_db = DBASE.session.get(User, test_user.id) 
    assert updated_user_from_db.name == new_name
    assert updated_user_from_db.email == new_email


@patch('app.modules.controllers.picture_validation')
@patch('app.modules.controllers.db.session.commit')
@patch('flask_login.utils._get_user')
def test_account_update_profile_picture(mock_get_user, mock_db_commit, mock_picture_validation, client, test_user, db):
    """Test POST to /auth/account with a picture."""
    mock_get_user.return_value = test_user
    mock_picture_validation.return_value = ("new_profile.jpg", True) # Simulate successful validation

    with client.session_transaction() as sess:
        sess['user_id'] = str(test_user.id)
        sess['_fresh'] = True

    # Werkzeug FileStorage needs a stream-like object
    from io import BytesIO
    mock_file = FileStorage(
        stream=BytesIO(b"fakeimgdata"),
        filename="testpic.jpg",
        content_type="image/jpeg"
    )

    response = client.post(url_for('auth.account'), data={
        'name': test_user.name,
        'email': test_user.email,
        'profile_picture': mock_file
    }, content_type='multipart/form-data', follow_redirects=True)

    assert response.status_code == 200
    assert url_for('auth.account') in response.request.path
    mock_picture_validation.assert_called_once()
    # Verify the file passed to picture_validation is the one we sent
    assert mock_picture_validation.call_args[0][0].filename == 'testpic.jpg'
    
    mock_db_commit.assert_called_once()
    updated_user_from_db = DBASE.session.get(User, test_user.id)
    assert updated_user_from_db.profile_image == "new_profile.jpg"
    assert b"Your information has been updated" in response.data


# --- Other Route Tests ---

def test_home_page_loads(client):
    """Test GET request to /."""
    # The '/' route is defined in app.modules.controllers using @app.route('/').
    # By default, Flask assigns the function name ('home') as the endpoint.
    response = client.get(url_for('home')) 
    assert response.status_code == 200
    assert b"Welcome to our Application" in response.data # Check for expected content from home.html

def test_welcome_page_loads_authenticated(client, logged_in_user):
    """Test GET to /auth/welcome when logged in. Uses logged_in_user fixture."""
    response = client.get(url_for('auth.welcome'))
    assert response.status_code == 200
    # Check for user-specific content, e.g., their name from the template.
    assert bytes(f"Welcome {logged_in_user.name}", 'utf-8') in response.data 

def test_welcome_page_redirects_unauthenticated(client):
    """Test GET to /auth/welcome when not logged in (should redirect to signin)."""
    response = client.get(url_for('auth.welcome'), follow_redirects=False) # Get initial redirect response
    assert response.status_code == 302 # Expecting a redirect
    assert url_for('auth.signin') in response.location # Check redirect location points to signin

def test_signin_redirects_if_already_authenticated(client, logged_in_user):
    """Test that /auth/signin redirects to welcome if user is already authenticated."""
    # The logged_in_user fixture ensures the session indicates an authenticated state.
    response = client.get(url_for('auth.signin'), follow_redirects=True)
    assert response.status_code == 200
    assert url_for('auth.welcome') in response.request.path # Should end up on the welcome page
    assert b"Welcome " + bytes(logged_in_user.name, 'utf-8') in response.data # Check welcome message

def test_register_redirects_if_already_authenticated(client, logged_in_user):
    """Test that /auth/register redirects to welcome if user is already authenticated."""
    # The logged_in_user fixture ensures the session indicates an authenticated state.
    response = client.get(url_for('auth.register'), follow_redirects=True)
    assert response.status_code == 200
    assert url_for('auth.welcome') in response.request.path
    assert b"Welcome " + bytes(logged_in_user.name, 'utf-8') in response.data
