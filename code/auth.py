import click
import functools
import stdiomask
import re
import sys
import string

from .db import get_db, commit
from .error import FormRequirementError, json_responses, JsonResponseError
from .model import User
from flask import Blueprint, render_template, url_for, session, g, request, redirect, current_app, flash, abort, jsonify
from flask.cli import with_appcontext
from werkzeug.security import check_password_hash, generate_password_hash
from hashlib import sha256
from os import urandom
from base64 import b64decode, b64encode

if sys.platform == 'win32':
    from msvcrt import getch
else:
    from stdiomask import getch

permissions = {
    'ADMIN': {'key': 'A', 'children': ('CALENDAR', 'NEWS', 'GALLERY', 'BULLETIN')},
    'CALENDAR': {'key':'C'},
    'NEWS': {'key':'N'},
    'GALLERY': {'key':'G'},
    'BULLETIN': {'key':'B'}
}

# this implies only two generations: parent & child.
# a recursive solution is needed if more generations are needed.
permission_parents = {k:[p for p, c in permissions.items() if c.get('children') and k in c['children']] for k in permissions}

username_requirements = {
    'LENGTH': {'message': 'Usernames must be between 5 and 20 characters', 'func': lambda x: 20 >= len(x) >= 5},
    'NO_SYMBOLS': {'message': 'Usernames can only have numbers and letters', 'func': lambda x: x.isalnum() }
}

password_requirements = {
    'LENGTH': {'message': 'Passwords must be between 8 and 20 characters', 'func': lambda x: 20 >= len(x) >= 8},
    'CAPITAL': {'message': 'Passwords must have at least 1 uppercase letter', 'func': lambda x: re.search("[A-Z]", x)},
    'LOWER': {'message': 'Passwords must have at least 1 lowercase letter', 'func': lambda x: re.search("[a-z]", x)},
    'NUMBER': {'message': 'Passwords must have at least 1 number', 'func': lambda x: re.search('[0-9]', x)},
    'ILLEGAL_SYMBOL': {'message': 'Password contains an invalid character', 'func': lambda x: \
        all(l in string.ascii_letters  + string.digits + string.punctuation for l in x) }
}

bp = Blueprint('auth', __name__)

@bp.route("/login", methods=['POST'])
def login():
    try:
        if not validate_token(request.form['token']):
            raise JsonResponseError('ERROR')
        elif not valid_login(request.form['username'], request.form['password']):
            raise JsonResponseError('FAIL', desc="Incorrect username or password")
        else:
            session.clear()
            session['username'] = request.form['username']
            return redirect(request.referrer or url_for('index'))
    except JsonResponseError as e:
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })

@bp.route('/signout')
def signout():
    session.clear()
    g.user = None
    return redirect(request.referrer if request.referrer and check_permissions() else url_for('index'))

def generate_token():
    if session.get('csrf_token') is None:
        m = sha256()
        m.update(urandom(32))
        token = b64encode(m.digest()).decode('ascii')
        session['csrf_token'] = token
    return session['csrf_token']

@bp.route('/token', methods=('GET',))
def get_token():
    generate_token()
    return jsonify({
        'token': session['csrf_token']
    })

def validate_token(token):
    return session.get('csrf_token') is not None and session.get('csrf_token') == token

def valid_login(username, password):
    user = User.query.filter(User.username == username).first()
    if user is None or not check_password_hash(user.password, password):
        return False
    else:
        return True

def valid_username(username):
    for _, v in username_requirements.items():
        if not v['func'](username):
            raise FormRequirementError(v['message'])
    return True


def valid_password(password):
    for _, v in password_requirements.items():
        if not v['func'](password):
            raise FormRequirementError(v['message'])
    return True

@bp.before_app_request
def verify_user():
    if session.get('username') is not None:
        g.user = User.query.filter(User.username == session.get('username')).first()
    else:
        g.user = None


def login_required(view_type=None):
    def decorator(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if check_permissions(view_type):
                return view(**kwargs)
            else:
                return abort(403)
        wrapped_view.__viewtype__ = view_type
        return wrapped_view

    return decorator

def check_permissions(view_type=None):
    return g.get('user') and \
        (not view_type or permissions[view_type]['key'] in g.user.permissions.upper() \
            or any(permissions[c]['key'] in g.user.permissions.upper() for c in permission_parents[view_type] ))

@click.command('register-admin')
@with_appcontext
def register_admin():
    username = 'admin'
    try:
        user = User.query.filter(User.username == username).first()
        if user:
            click.echo("WARNING: Admin account already exists. Press 'Y' to continue anyway...")
            x = stdiomask.getch()
            if isinstance(x, bytes):
                x = x.decode()
            if x.upper() != 'Y':
                click.echo("Aborted.")
                return
            else:
                get_db().delete(user)
                commit()
        m = sha256()
        m.update(urandom(8))
        password = b64encode(m.digest()).decode('ascii')

        admin = User(username, generate_password_hash(password), 'A')
        db = get_db()
        db.add(admin)
        commit()

        click.echo("\nCreated temporary user '%s'" % username)
        click.echo("Password: %s" % password)
        click.echo("PLEASE REMOVE THIS ACCOUNT OR CHANGE ITS PASSWORD WHEN YOU'RE DONE WITH IT")
        # TODO: this exception should be specific to DB issues
    except Exception as e:
        click.echo("Error creating user")
        click.echo(e)