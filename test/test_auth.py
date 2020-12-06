import pytest
from flask import session, g
from test.utils import populate_user_table

auth_user_table = [
    ('johnsmith', 'mypassword1', 'A'),
    ('newsman', 'idothenews13', 'N')
]

tables = ('user')

@pytest.fixture
def db_session(db_session_init):
    import code.db
    db = code.db.get_db()
    engine = db.get_bind()

    yield code.db.get_db()
    for table in [t for t in reversed(code.db.Base.metadata.sorted_tables) if t.name in tables]:
        engine.execute(table.delete())


def test_login(client, db_session, csrf_token):
    populate_user_table(db_session, auth_user_table)
    username, password, *_ = auth_user_table[0]

    with client:
        # token initialization
        token = None
        with client.session_transaction() as s:
            token = csrf_token(s)
        
        # TODO: anything i can do about this copy paste code?

        # TEST 1: positive test
        response = client.post('/login', data={'username': username, 'password':password, 'token': token}, follow_redirects=True)
        assert response.status_code == 200 and not response.is_json
        assert session.get('username') == username

        # rollback user
        with client.session_transaction() as s:
            s.clear()
            token = csrf_token(s)

        # TEST 2: incorrect user
        response = client.post('/login', data={'username': 'notoneIhave', 'password':password, 'token': token}, follow_redirects=True)
        assert response.status_code == 200 and response.is_json
        assert session.get('username') != username
        assert response.json.get('STATUS') == 'FAIL'

        # rollback user
        with client.session_transaction() as s:
            s.clear()
            token = csrf_token(s)

        # TEST 3: incorrect password
        response = client.post('/login', data={'username': username, 'password':'pass', 'token': token}, follow_redirects=True)
        assert response.status_code == 200 and response.is_json
        assert session.get('username') != username
        assert response.json.get('STATUS') == 'FAIL'

        # rollback user
        with client.session_transaction() as s:
            s.clear()
            token = csrf_token(s)

        # TEST 4: invalid csrf token
        response = client.post('/login', data={'username': username, 'password':password, 'token': 'nottoken'}, follow_redirects=True)
        assert response.status_code == 200 and response.is_json
        assert session.get('username') != username
        assert response.json.get('STATUS') == 'ERROR'

        
def test_signout(client, db_session):
    username = 'johnsmith'
    with client:
        with client.session_transaction() as s:
            s['username'] = username

        # TEST 1: positive case
        response = client.get('/signout', follow_redirects=True)
        assert response.status_code == 200 and response.mimetype == 'text/html'
        assert session.get('username') != username

def test_get_token(client, db_session):
    populate_user_table(db_session, auth_user_table)
    with client:

        # TEST 1: positive case
        response = client.get('/token')
        assert response.status_code == 200 and response.is_json
        assert session.get('csrf_token') == response.json['token']

def test_check_permissions(app_context, db_session):
    from code.auth import check_permissions
    # TODO: stub out User??
    from code.model import User

    populate_user_table(db_session, auth_user_table)
    admin_username, *_ = auth_user_table[0]
    news_username, *_ = auth_user_table[1]

    permission_types = (None, 'NEWS', 'ADMIN')

    with app_context:

        # TEST 1: no authentication presented
        result = check_permissions()
        assert not result

        # TEST 2: authentication, minimal authorized
        g.user = User.query.filter(User.username == news_username).first()
        
        for permission_type, expected in zip(permission_types, (True, True, False)):
            result = check_permissions(permission_type)
            assert result == expected

        # TEST 3: admin authorized
        g.user = User.query.filter(User.username == admin_username).first()

        for permission_type, expected in zip(permission_types, (True, True, True)):
            result = check_permissions(permission_type)
            assert result == expected

# TODO: how am i gonna test valid_form_entry()....?
