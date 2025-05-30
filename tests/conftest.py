# This file will contain shared fixtures for pytest.
import pytest
from app import app as flask_app, db as sqlalchemy_db

@pytest.fixture(scope='session')
def app():
    """
    Session-wide test `Flask` application.
    
    This fixture creates a new Flask application instance for each test session,
    configured for testing. It uses an in-memory SQLite database, disables CSRF
    protection for forms, and sets SERVER_NAME to allow `url_for` to work
    without an active request context in some situations.
    Database tables are created before tests and dropped after.
    """
    # Setup testing config
    flask_app.config.update({
        "TESTING": True,
        "DEBUG": True,
        "WTF_CSRF_ENABLED": False, # Disable CSRF for simpler form testing
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", # Use in-memory SQLite
        # SERVER_NAME is important for url_for to work correctly in tests
        # when not in a request context or when testing outside of a request.
        "SERVER_NAME": "localhost.localdomain" 
    })

    # Establish an application context before running the tests.
    with flask_app.app_context():
        sqlalchemy_db.create_all() # Create database tables
        yield flask_app # This is where the testing happens
        sqlalchemy_db.drop_all() # Drop database tables after tests
        sqlalchemy_db.session.remove() # Ensure session is closed

@pytest.fixture()
def client(app):
    """
    A test client for the app.
    """
    return app.test_client()

@pytest.fixture()
def db(app):
    """
    Provides the SQLAlchemy database instance.
    
    This fixture yields the `sqlalchemy_db` object within an application context,
    making it available for tests to interact with the database.
    The actual database creation and teardown (drop_all) are handled by the
    session-scoped `app` fixture. This `db` fixture is function-scoped by default
    if not specified, meaning it runs per test function, leveraging the app context
    provided by the `app` fixture.
    """
    with app.app_context():
        yield sqlalchemy_db
        # For function-scoped database state management (if not using a transaction manager):
        # sqlalchemy_db.session.remove() # Clean session after each test
        # sqlalchemy_db.session.rollback() # Optional: ensure no pending transactions
# Note: The primary db cleanup (drop_all) is session-scoped in the `app` fixture.
# Individual tests using this `db` fixture operate within that session's DB lifecycle.
