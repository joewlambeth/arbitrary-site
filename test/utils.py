from werkzeug.security import generate_password_hash
from functools import wraps
from unittest.mock import patch

def populate_user_table(db, user_table):
    for username, password, permissions in user_table:
        db.execute("INSERT into user (username, password, permissions) VALUES ('%s', '%s', '%s');" % (username, generate_password_hash(password), permissions))
    db.commit()

def populate_group_table(db, group_table):
    for title, description, grouptype in group_table:
        db.execute("INSERT into groups (title, description, grouptype) VALUES ('%s', '%s', %d);" % (title, description, grouptype))
    db.commit()

def kwarg_error(func_name, parameter, kwargs):
    if parameter not in kwargs:
        raise ValueError("Missing keyword argument '%s' for %s()", (parameter, func_name))