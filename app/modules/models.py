# Import the database object (db) from the main application module
# We will define this inside /app/__init__.py in the next sections.
from app import db ,login_manager
from flask_login import UserMixin
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# Define a base model for other database tables to inherit
class Base(db.Model):

    __abstract__  = True

    id            = db.Column(db.Integer, primary_key=True)
    date_created  = db.Column(db.DateTime,  default=db.func.current_timestamp())
    date_modified = db.Column(db.DateTime,  default=db.func.current_timestamp(),
                                           onupdate=db.func.current_timestamp())

# Define a User model
class User(Base,UserMixin):

    __tablename__ = 'auth_user'

    # User Name
    name    = db.Column(db.String(128),  nullable=False)

    # Identification Data: email & password
    email    = db.Column(db.String(128),  nullable=False,
                                            unique=True)
    password = db.Column(db.String(192),  nullable=False)
    profile_image = db.Column(db.String(255),  nullable=False, default='default.png')

    # Authorisation Data: role & status
    role     = db.Column(db.SmallInteger, nullable=False)
    status   = db.Column(db.SmallInteger, nullable=False)

    # New instance instantiation procedure
    def __init__(self, name, email, password,role,status):

        self.name     = name
        self.email    = email
        self.password = password
        self.role = role
        self.status = status

    def __repr__(self):
        return '<User %r>' % (self.name)  
