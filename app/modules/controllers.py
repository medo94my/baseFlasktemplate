# Import flask dependencies
from flask import Blueprint, request, render_template, \
                  flash, g, session, redirect, url_for,Flask

# Import password / encryption helper tools
from werkzeug.security  import check_password_hash, generate_password_hash

# Import the database object from the main app module
from app import db,app

# Import module forms
from app.modules.forms import LoginForm,RegisterForm,UpdateUserFrom

# Import module models (i.e. User)
from app.modules.models import User
from app.modules.Image import picture_validation
# import login manager
from flask_login import login_user ,current_user,logout_user,login_required

# Define the blueprint: 'auth', set its url prefix: app.url/auth
mod_auth = Blueprint('auth', __name__, url_prefix='/auth')
# Set the route and accepted methods
@mod_auth.route('/signin/', methods=['GET', 'POST'])
def signin():
    if current_user.is_authenticated:
        return redirect(url_for('auth.welcome'))
    # If sign in form is submitted
    form = LoginForm(request.form)

    # Verify the sign in form
    if request.method == 'POST' and  form.validate():

        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page=request.args.get('next')
            # print(next_page)
            # session['user_id'] = user.id
            flash('Welcome %s' % current_user.name ,'success')
            return redirect(next_page) if next_page else redirect(url_for('auth.welcome'))

        flash('Login unsuccessful, Please check email and password','danger')

    return render_template("auth/signin.html", form=form)

@mod_auth.route('/register/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.welcome'))
    # If sign up form is submitted
    form = RegisterForm(request.form)
    # Verify the sign in form
    if request.method == 'POST' and form.validate():
        try:
            user=User(
            name=form.name.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            role=1,
            status=1
            )
            db.session.add(user)
            db.session.commit()
            flash('you are now registered and can login', 'success')
            return redirect(url_for('auth.signin'))
        except Exception as err:
            flash(err,'danger')
            print(err)
            # return request.referrer
            
       
       
        # user = User.query.filter_by(email=form.email.data).first()

        # # if user and check_password_hash(user.password, form.password.data):

        # #     session['user_id'] = user.id

        # #     flash('Welcome %s' % user.name)

        # #     return redirect(url_for('auth.signin'))

        # # flash('Wrong email or password', 'error-message')

    return render_template("auth/signup.html", form=form)



@login_required
@mod_auth.route('/welcome')
def welcome():
    return render_template("welcome.html")
# Main page
@app.route('/')
def home():
    return render_template("home.html")

# Log out user
@login_required
@mod_auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


# user account
@mod_auth.route('/account',methods=['GET','POST'])
@login_required
def account():
    form=UpdateUserFrom(request.form)
    if request.method == 'POST' and form.validate():
        image=request.files['profile_picture']
        print(image)
        if image.filename != '':
            id=current_user.id
            print(id)
            pic=picture_validation(image,id)
            if pic[1]==False:
                flash(f'file extention is not allowed only { pic[0][0]},{pic[0][1]}','danger')
                return redirect(url_for('auth.account'))
            else:
                current_user.profile_image=pic[0]
        current_user.name=form.name.data
        current_user.email=form.email.data
        db.session.commit()  
        flash('Your information has been updated','success')
        return redirect(url_for('auth.account'))
    elif  request.method == 'GET':
        form.name.data=current_user.name
        form.email.data=current_user.email
    image_file=url_for('static',filename='img/profile_pics/'+ current_user.profile_image)
    return render_template('auth/account.html',form=form, profile_imge=image_file)
