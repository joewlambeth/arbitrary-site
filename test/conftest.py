import pytest
import os
from unittest.mock import patch
from functools import wraps

print(os.getcwd())

from code.main import app as flask_app

@pytest.fixture(scope="session")
def app():
    flask_app.config['TESTING'] = True
    yield flask_app

@pytest.fixture
def app_context(app):
    return app.app_context()

@pytest.fixture
def url_mapping(app):
    mapping = dict()
    with app.app_context() as context:
        for rule in app.url_map.iter_rules():
            mapping[rule.endpoint] = {'url': str(rule), 'func': app.view_functions[rule.endpoint]}
    return mapping

@pytest.fixture
def client(app):
    yield app.test_client()

@pytest.fixture(scope="session")
def db_session_init():
    import code.db
    db = code.db.get_db()
    engine = db.get_bind()
    code.db.Base.metadata.create_all(engine)
    yield 
    code.db.Base.metadata.drop_all(engine)  
    

@pytest.fixture
def csrf_token(app):
    from flask import session
    token = 'abcdefghijklmnop'

    def set_csrf_token(temp_session):
        temp_session['csrf_token'] = token
        return token

    yield set_csrf_token

    # with app.test_request_context():
    #     session['csrf_token'] = token
    #     # return token

    #     yield token

    #     session['csrf_token'] = 'NO LONGER VALID TOKEN'

# @pytest.fixture
# def insert_db_data():
#     engine.execute("INSERT INTO user VALUES ('testuser1', '', 'CNG')")
#     engine.execute("INSERT INTO post VALUES ('testuser1', '', 'CNG')")