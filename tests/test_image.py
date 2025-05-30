import pytest
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import FileStorage
from app.modules.Image import picture_validation, save_picture
from app.modules.models import User # Needed for save_picture context
from app import db as DBASE # To handle potential db interactions if user object is updated

# Allowed extensions are defined in Image.py, let's assume for testing:
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
# And save_picture uses current_user from flask_login for user context

@pytest.fixture
def mock_current_user():
    """Fixture for a mock current_user object with an ID."""
    user = MagicMock(spec=User)
    user.id = 1
    user.profile_image = 'default.png' # Default state
    return user

def test_picture_validation_allowed_extension():
    """Test picture_validation with allowed extensions."""
    mock_file = MagicMock(spec=FileStorage)
    
    mock_file.filename = 'test.jpg'
    result = picture_validation(mock_file, user_id=1)
    assert result[0] == 'test.jpg' # filename or new filename if save_picture was fully run
    assert result[1] is True # Indicates success

    mock_file.filename = 'image.PNG' # Test case insensitivity
    result = picture_validation(mock_file, user_id=1)
    assert result[0].lower().endswith('.png') # save_picture might rename it
    assert result[1] is True

    mock_file.filename = 'photo.jpeg'
    result = picture_validation(mock_file, user_id=1)
    assert result[0].lower().endswith('.jpeg')
    assert result[1] is True

@patch('app.modules.Image.save_picture') # Mock save_picture within picture_validation
def test_picture_validation_calls_save_picture(mock_save_picture):
    """Test that picture_validation calls save_picture for allowed extensions."""
    mock_save_picture.return_value = "saved_image_name.jpg" # Mock its return
    
    mock_file = MagicMock(spec=FileStorage)
    mock_file.filename = 'test.jpg'
    
    filename, success = picture_validation(mock_file, user_id=1)
    
    mock_save_picture.assert_called_once_with(mock_file, 1)
    assert success is True
    assert filename == "saved_image_name.jpg"

def test_picture_validation_disallowed_extension():
    """Test picture_validation with a disallowed extension."""
    mock_file = MagicMock(spec=FileStorage)
    mock_file.filename = 'document.txt'
    
    # Expected return based on current Image.py: (ALLOWED_EXTENSIONS, False)
    # Let's refine this based on actual implementation if it differs
    # For now, assuming it returns a tuple where the second element is False for failure
    filename_or_allowed_ext, success = picture_validation(mock_file, user_id=1)

    assert success is False
    # filename_or_allowed_ext might contain the list of allowed extensions
    assert isinstance(filename_or_allowed_ext, (list, set, tuple)) 
    assert 'txt' not in [ext.lower() for ext in filename_or_allowed_ext]


@patch('app.modules.Image.current_user', new_callable=MagicMock) # Patches the global current_user in Image.py if used
@patch('app.modules.Image.os.path.exists')      # Mocks os.path.exists
@patch('app.modules.Image.os.remove')         # Mocks os.remove
@patch('app.modules.Image.secrets.token_hex', return_value='randomhex') # Mocks token_hex
@patch('app.modules.Image.Image.open')        # Mocks Pillow's Image.open
@patch('app.modules.Image.app')               # Mocks the 'app' object imported in Image.py (for app.root_path)
def test_save_picture_new_image(
    mock_app_obj, mock_image_open, mock_secrets_token_hex, mock_os_remove_call, mock_os_path_exists_call,
    mock_current_user_in_image_module,  # Corresponds to @patch('app.modules.Image.current_user')
    db, mock_current_user # Fixtures
):
    """
    Test save_picture successfully saving a new image when the user has no previous custom image.
    Verifies file operations (Pillow, os) and correct filename generation.
    Note: The 'user_id' param of save_picture is used to fetch & update the user,
          so direct modification of a global `current_user` for profile_image update isn't the primary mechanism.
          The `mock_current_user_in_image_module` is more of a safeguard if any part of `save_picture`
          unexpectedly tries to use a globally imported `current_user`.
    """
    # Setup the user object that User.query.filter_by().first() will return
    user_to_update = User(id=mock_current_user.id, profile_image='default.png')
    
    # Mock app.root_path as used in save_picture
    mock_app_obj.root_path = '/fake/app/path'

    # Mock Image.open() to return a mock PIL image object
    mock_pil_image = MagicMock()
    mock_pil_image.thumbnail.return_value = None # thumbnail modifies in place
    mock_image_open.return_value = mock_pil_image

    mock_form_picture = MagicMock(spec=FileStorage)
    mock_form_picture.filename = 'test.jpg'

    # Simulate that the old picture (default.png) does not trigger an os.remove call.
    # os.path.exists would be called for 'default.png' if logic tries to remove it.
    mock_os_path_exists_call.return_value = False 

    with patch('app.modules.Image.User.query') as mock_user_query:
        mock_user_query.filter_by(id=mock_current_user.id).first.return_value = user_to_update

        saved_filename = save_picture(mock_form_picture, mock_current_user.id)

    # Assertions
    expected_filename = "randomhex.jpg" # Based on mock_secrets_token_hex and original extension
    assert saved_filename == expected_filename
    
    # Check path construction for Pillow's save method
    expected_save_path = '/fake/app/path/static/img/profile_pics/randomhex.jpg'
    
    mock_image_open.assert_called_once_with(mock_form_picture)
    assert mock_pil_image.thumbnail.called # Check if thumbnail was called
    mock_pil_image.save.assert_called_once_with(expected_save_path)
    
    # os.remove should not be called if previous image is default.png or path doesn't exist
    mock_os_remove_call.assert_not_called()

@patch('app.modules.Image.current_user', new_callable=MagicMock)
@patch('app.modules.Image.os.path.exists')
@patch('app.modules.Image.os.remove')
@patch('app.modules.Image.secrets.token_hex', return_value='newrandomhex')
@patch('app.modules.Image.Image.open')
@patch('app.modules.Image.app')
def test_save_picture_replaces_existing(
    mock_app_obj, mock_image_open, mock_secrets_token_hex, mock_os_remove_call, mock_os_path_exists_call,
    mock_current_user_in_image_module, db, mock_current_user
):
    """
    Test save_picture replacing an existing (non-default) user profile image.
    Verifies that the old image file is removed.
    """
    user_to_update = User(id=mock_current_user.id, profile_image='old_image.jpg') # Existing image

    mock_app_obj.root_path = '/fake/app/path'
    
    mock_pil_image = MagicMock()
    mock_pil_image.thumbnail.return_value = None
    mock_image_open.return_value = mock_pil_image

    mock_form_picture = MagicMock(spec=FileStorage)
    mock_form_picture.filename = 'new_photo.png'

    # Simulate that the old picture file exists, so it should be removed
    mock_os_path_exists_call.return_value = True 
    
    with patch('app.modules.Image.User.query') as mock_user_query:
        mock_user_query.filter_by(id=mock_current_user.id).first.return_value = user_to_update
        saved_filename = save_picture(mock_form_picture, mock_current_user.id)

    expected_new_filename = "newrandomhex.png"
    assert saved_filename == expected_new_filename

    expected_old_image_path = '/fake/app/path/static/img/profile_pics/old_image.jpg'
    # Check that os.path.exists was called for the old image path
    mock_os_path_exists_call.assert_called_once_with(expected_old_image_path)
    # Check that os.remove was called for the old image path
    mock_os_remove_call.assert_called_once_with(expected_old_image_path)

    expected_new_save_path = '/fake/app/path/static/img/profile_pics/newrandomhex.png'
    mock_pil_image.save.assert_called_once_with(expected_new_save_path)

@patch('app.modules.Image.save_picture', side_effect=Exception("PIL error"))
def test_picture_validation_handles_save_picture_exception(mock_save_picture_exception):
    """
    Test how picture_validation reacts if save_picture raises an unhandled exception.
    The current picture_validation does not have specific error handling for save_picture failures.
    """
    mock_file = MagicMock(spec=FileStorage)
    mock_file.filename = 'test.jpg' # Allowed extension
    
    # If save_picture fails (e.g., PIL issue, disk full), and picture_validation
    # doesn't catch it, the exception will propagate. This test verifies that.
    with pytest.raises(Exception, match="PIL error"):
         picture_validation(mock_file, user_id=1)

# Note: The following test was previously written and is good.
# It focuses on the DB interaction part of save_picture.
# The parameter names in the decorator were a bit confusing, so adjusted for clarity.
@patch('app.modules.Image.current_user', new_callable=MagicMock) 
@patch('app.modules.Image.db')                                   
@patch('app.modules.Image.os.path.exists', return_value=False)   
@patch('app.modules.Image.os.remove')                            
@patch('app.modules.Image.secrets.token_hex', return_value='dbtesthex') 
@patch('app.modules.Image.Image.open')                           
@patch('app.modules.Image.app')                                  
def test_save_picture_updates_user_model_and_commits(
    mock_app_obj, mock_image_open, mock_secrets_token_hex, mock_os_remove_call, mock_os_path_exists_call,
    mock_db_in_image_module, mock_current_user_in_image_module, # These correspond to the patches on app.modules.Image
    db, mock_current_user # Fixtures
):
    """
    Test that save_picture correctly updates the user's profile_image attribute
    in the database and commits the session.
    """
    mock_app_obj.root_path = '/fake/app/path' # Configure mock app.root_path
    
    # This is the user object that User.query.filter_by().first() will return.
    # save_picture will modify this user's profile_image attribute.
    user_for_save_picture = User(id=mock_current_user.id, name="DB Test", email="db@test.com", profile_image='default.png')
    
    # Mock the PIL Image object and its methods
    mock_pil_image = MagicMock()
    mock_pil_image.thumbnail.return_value = None
    mock_image_open.return_value = mock_pil_image

    # Mock the uploaded file object
    mock_form_picture = MagicMock(spec=FileStorage)
    mock_form_picture.filename = 'db_interaction.png'
    
    # Ensure User.query.filter_by(id=...).first() returns our user_for_save_picture
    with patch('app.modules.Image.User.query') as mock_user_query:
        mock_user_query.filter_by(id=mock_current_user.id).first.return_value = user_for_save_picture
        
        saved_filename = save_picture(mock_form_picture, mock_current_user.id)

    # Verify the user's profile_image attribute was updated
    assert user_for_save_picture.profile_image == "dbtesthex.png"
    # Verify that db.session.commit() was called (via the mock_db_in_image_module)
    mock_db_in_image_module.session.commit.assert_called_once()

    assert saved_filename == "dbtesthex.png"
    mock_app.root_path = '/fake/app/path'

    # Mock Image.open() to return a mock image object
    mock_pil_image = MagicMock()
    mock_pil_image.resize.return_value = mock_pil_image # if resize is used
    mock_pil_image.thumbnail.return_value = None # thumbnail modifies in place
    mock_img_open.return_value = mock_pil_image

    mock_form_picture = MagicMock(spec=FileStorage)
    mock_form_picture.filename = 'test.jpg'

    # Simulate that the old picture (default.png) does not exist or we don't try to remove it
    mock_os_path_exists.return_value = False 

    # Call the function
    saved_filename = save_picture(mock_form_picture, mock_current_user.id)

    # Assertions
    expected_filename = "randomhex.jpg"
    assert saved_filename == expected_filename
    
    # Check path construction
    expected_save_path = '/fake/app/path/static/img/profile_pics/randomhex.jpg'
    
    mock_img_open.assert_called_once_with(mock_form_picture)
    # In the actual code, it's `i.thumbnail(output_size)`
    # Check if thumbnail was called (exact args depend on output_size in save_picture)
    assert mock_pil_image.thumbnail.called 
    
    mock_pil_image.save.assert_called_once_with(expected_save_path)
    
    mock_os_remove.assert_not_called() # Should not be called if previous image is default.png or doesn't exist

@patch('app.modules.Image.current_user', new_callable=MagicMock)
@patch('app.modules.Image.os.path.exists')
@patch('app.modules.Image.os.remove')
@patch('app.modules.Image.secrets.token_hex', return_value='newrandomhex')
@patch('app.modules.Image.Image.open')
@patch('app.modules.Image.app')
def test_save_picture_replaces_existing(mock_app, mock_img_open, mock_token_hex, mock_os_remove, mock_os_path_exists, mock_current_user_global, db, mock_current_user):
    """Test save_picture replacing an existing image."""
    
    # Setup current_user with an existing (non-default) image
    mock_current_user_global.id = mock_current_user.id
    mock_current_user_global.profile_image = 'old_image.jpg' # Existing image

    mock_app.root_path = '/fake/app/path'
    
    mock_pil_image = MagicMock()
    mock_pil_image.thumbnail.return_value = None
    mock_img_open.return_value = mock_pil_image

    mock_form_picture = MagicMock(spec=FileStorage)
    mock_form_picture.filename = 'new_photo.png'

    # Simulate that the old picture file exists
    mock_os_path_exists.return_value = True 
    
    saved_filename = save_picture(mock_form_picture, mock_current_user.id)

    expected_new_filename = "newrandomhex.png"
    assert saved_filename == expected_new_filename

    expected_old_image_path = '/fake/app/path/static/img/profile_pics/old_image.jpg'
    mock_os_path_exists.assert_called_once_with(expected_old_image_path)
    mock_os_remove.assert_called_once_with(expected_old_image_path)

    expected_new_save_path = '/fake/app/path/static/img/profile_pics/newrandomhex.png'
    mock_pil_image.save.assert_called_once_with(expected_new_save_path)

@patch('app.modules.Image.save_picture', side_effect=Exception("PIL error"))
def test_picture_validation_handles_save_picture_exception(mock_save_picture_exception):
    """Test that picture_validation handles exceptions from save_picture gracefully."""
    mock_file = MagicMock(spec=FileStorage)
    mock_file.filename = 'test.jpg' # Allowed extension

    # We expect picture_validation to catch the exception and return success=False
    # and some form of error message or the allowed extensions.
    # This depends on the actual error handling in picture_validation.
    # Assuming it returns (ALLOWED_EXTENSIONS, False) or similar on error.
    
    # The current picture_validation doesn't have explicit try-except for save_picture
    # If save_picture fails, picture_validation will fail.
    # This test is more of a design consideration. If picture_validation should be more robust:
    with pytest.raises(Exception, match="PIL error"):
         picture_validation(mock_file, user_id=1)

    # If picture_validation *did* handle it:
    # filename_or_info, success = picture_validation(mock_file, user_id=1)
    # assert success is False
    # assert "PIL error" in str(filename_or_info) # Or check for specific error message
    # For now, the test above (with pytest.raises) is more accurate to current code.

# Note: The actual `save_picture` in the provided code updates `current_user.profile_image`
# and calls `db.session.commit()`. Tests for these side effects would require
# mocking `db.session.commit` and verifying `current_user.profile_image` is updated.
# The provided tests focus on file operations and PIL interactions.
# I'll add a test for the database interaction part of save_picture.

@patch('app.modules.Image.current_user', new_callable=MagicMock) # Mocks current_user in Image.py
@patch('app.modules.Image.db') # Mocks db in Image.py
@patch('app.modules.Image.os.path.exists', return_value=False) # Assume no old files
@patch('app.modules.Image.os.remove')
@patch('app.modules.Image.secrets.token_hex', return_value='dbtesthex')
@patch('app.modules.Image.Image.open')
@patch('app.modules.Image.app')
def test_save_picture_updates_user_model_and_commits(
    mock_app_root, mock_img_open, mock_token_hex, mock_os_remove, mock_os_path_exists,
    mock_db_global, mock_current_user_global, db, mock_current_user # test fixtures
):
    # Configure the global mocks that save_picture will use
    mock_app_root.root_path = '/fake/app/path'
    
    # User object that current_user in Image.py will be mocked with
    # We need to ensure this mock_current_user_global is what save_picture sees
    user_for_save_picture = User(id=mock_current_user.id, name="Test", email="test@test.com", profile_image='default.png')
    
    # Instead of mocking current_user directly in the global scope of Image.py via patch,
    # it's often cleaner if save_picture took the user object as a parameter.
    # Since it uses global current_user, we patch it at 'app.modules.Image.current_user'
    mock_current_user_global.id = user_for_save_picture.id
    mock_current_user_global.profile_image = user_for_save_picture.profile_image
    # We also need to mock User.query.filter_by().first() if it's used to fetch the user
    # The provided save_picture directly modifies the global current_user.

    mock_pil_image = MagicMock()
    mock_pil_image.thumbnail.return_value = None
    mock_img_open.return_value = mock_pil_image

    mock_form_picture = MagicMock(spec=FileStorage)
    mock_form_picture.filename = 'db_interaction.png'

    # Call the function - user_id argument is actually used to fetch user in original code
    # The save_picture function in snippet uses `current_user.id` and modifies `current_user.profile_image`
    # It does NOT use the user_id parameter to fetch the user. This is a discrepancy.
    # Let's assume the version of save_picture being tested is the one that uses global current_user.
    
    # If save_picture was: def save_picture(form_picture): # and used global current_user
    # This would be the call:
    # saved_filename = save_picture(mock_form_picture)

    # The actual save_picture is: def save_picture(form_picture, user_id):
    # And it does:
    #   user = User.query.filter_by(id=user_id).first()
    #   ...
    #   user.profile_image = picture_fn
    #   db.session.commit()
    # So we need to mock User.query.filter_by().first()

    with patch('app.modules.Image.User.query') as mock_user_query:
        mock_user_query.filter_by(id=mock_current_user.id).first.return_value = user_for_save_picture
        
        saved_filename = save_picture(mock_form_picture, mock_current_user.id)

        assert user_for_save_picture.profile_image == "dbtesthex.png"
        mock_db_global.session.commit.assert_called_once()

    assert saved_filename == "dbtesthex.png"
