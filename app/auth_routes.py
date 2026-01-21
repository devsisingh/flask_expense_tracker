from flask import Blueprint, render_template, request, redirect
from flask_login import login_user, logout_user, login_required
from .models import db, User

auth = Blueprint('auth', __name__)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    error=None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            error = "User already exists"
            return render_template('register.html', error=error, username=username)

        user = User(username=username)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect('/')

    return render_template('register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    error=None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect('/')
        else:
            error = "Incorrect username or password"

    return render_template('login.html', error=error)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')
