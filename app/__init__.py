# Import flask and template operators
from flask import Flask, render_template

# Import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
# Define the WSGI application object
app = Flask(__name__)

# Configurations
app.config.from_object('config')

# Define the database object which is imported
# by modules and controllers
db = SQLAlchemy(app)
login_manager=LoginManager(app)
login_manager.login_view='auth.signin'
login_manager.login_message_category='info'
# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

# Import a module / component using its blueprint handler variable (mod_auth)
# from app.modules.controllers import mod_auth as auth_module

# Register blueprint(s)
# app.register_blueprint(auth_module)
# app.register_blueprint(xyz_module)
# ..

# Automatically discover and register blueprints
import os
import importlib
from flask import Blueprint

def register_blueprints(app_instance):
    """
    Automatically discovers and registers blueprints from the 'app/modules' directory.
    
    This function scans for .py files (excluding __init__.py) in the 'app/modules'
    directory. For each file, it imports the module and searches for attributes
    that are instances of Flask's Blueprint class. Any such Blueprint objects found
    are then registered with the Flask application instance.
    
    For example, if you have 'app/modules/example_routes.py' containing a
    Blueprint instance like `example_bp = Blueprint('example', __name__)`,
    this function will find and register `example_bp`.
    It's good practice to name blueprint variables descriptively (e.g., `mod_auth`, `admin_bp`).
    """
    app_path = os.path.dirname(__file__)
    modules_path = os.path.join(app_path, 'modules')
    if not os.path.exists(modules_path):
        print(f"Warning: Modules directory '{modules_path}' not found. No blueprints will be registered.")
        return

    for filename in os.listdir(modules_path):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = f"app.modules.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                for item_name in dir(module):
                    item = getattr(module, item_name)
                    if isinstance(item, Blueprint):
                        app_instance.register_blueprint(item)
                        print(f"Registered blueprint '{item.name}' from {module_name}")
            except Exception as e:
                print(f"Error importing or registering blueprint from {module_name}: {e}")

register_blueprints(app)

# Build the database:
# This will create the database file using SQLAlchemy
db.create_all()

