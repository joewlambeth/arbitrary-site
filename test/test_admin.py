# from code.model import GroupEnum
import pytest
from test.utils import populate_user_table, populate_group_table, kwarg_error
from flask import session, url_for
from werkzeug.security import check_password_hash

grouptype_map = ['_', 'groups', 'connect']

admin_user_table = [
    ('admin_user', 'adminpassword', 'A'),
    ('not_admin', 'anotherpassword', 'N'),
    ('dummyuser', 'somedummypassword', 'N')
]

admin_group_table = [
    ('My Group 1', 'This is a group of undefined purpose', 1), # can't import GroupEnum, since Base is outside application context
    ('My Connect 1', 'This is a connect of undefined purpose', 2)
]

tables = ('user', 'groups')

@pytest.fixture
def db_session(db_session_init):
    import code.db
    db = code.db.get_db()
    engine = db.get_bind()

    yield code.db.get_db()
    for table in [t for t in reversed(code.db.Base.metadata.sorted_tables) if t.name in tables]:
        engine.execute(table.delete())

# TODO: is this the 'canon' way to do boilerplate stuff?
def boilerplate(client, db_session, url_mapping, func_name, *test_functions, **kwargs):
    populate_user_table(db_session, admin_user_table)
    populate_group_table(db_session, admin_group_table)

    good_user = admin_user_table[0][0]

    endpoint = url_mapping[func_name]['url']
    endpoint_func = url_mapping[func_name]['func']

    with client:
        with client.session_transaction() as s:
            s['username'] = good_user

        for test_function in test_functions:
            test_function(client, db_session, endpoint, **kwargs)            

        assert '__viewtype__' in dir(endpoint_func) and endpoint_func.__viewtype__ == 'ADMIN'
        # TODO: do negative case for login_required JUST IN CASE

def btest_404(client, db_session, endpoint, **kwargs):
    current_endpoint = endpoint.replace('<int:id>', str('9001'))
    data_type = 'data'
    data = dict()
    post_request = True
    if 'data' in kwargs:
        data = kwargs['data']
    elif 'json' in kwargs:
        data = kwargs['json']
        data_type = 'json'
    else:
        post_request = False
    if post_request:
        response = client.post(current_endpoint, **{data_type:data})
    else:
        response = client.get(current_endpoint)
    assert response.status_code == 404
    

# note, this is called INSIDE individual tests, as opposed to a standalone, like 404
def btest_csrf(client, db_session, endpoint, **kwargs):
    data_type = None
    try:
        kwarg_error('btest_csrf', 'data', kwargs)
        data_type = 'data'
    except ValueError:
        kwarg_error('btest_csrf', 'json', kwargs)
        data_type = 'json'

    current_endpoint = endpoint
    if 'id' in kwargs:
        current_endpoint = endpoint.replace('<int:id>', str(kwargs['id']))

    data = {k:v for k, v in kwargs[data_type].items()}
    data['token'] = 'unusedtoken'

    response = client.post(current_endpoint, **{data_type:data})
    assert response.status_code == 200 and response.is_json

    response_data = response.json
    assert response_data['STATUS'] == 'ERROR'


def test_index(client, db_session, url_mapping):
    func_name = 'admin.index'
    def test(client, db_session, endpoint, **kwargs):
        # TEST 1 : positive test
        
        response = client.post(endpoint)
        assert response.status_code == 200 and response.is_json
        
        data = response.json
        assert 'permissions' in data and 'groups' in data
        
        # quickly check if groups is returned, lazy or otherwise
        # i don't compare attributes because requirements for what columns are needed could change

        result_set = db_session.execute("SELECT id, title FROM groups").fetchall()
        assert len(data['groups']) == len(result_set)


    boilerplate(client, db_session, url_mapping, func_name, test)
        
def test_list_users(client, db_session, url_mapping):
    func_name = 'admin.list_users'
    def test(client, db_session, endpoint, **kwargs):
        # TEST 1: positive case
        response = client.get(endpoint)
        assert response.status_code == 200 and response.is_json
        result_set = db_session.execute("SELECT id, username FROM user").fetchall()
        
        names = {str(i): username for i, username in result_set}
        data = response.json
        
        assert sorted(data.get('NAMES')) == sorted(names)

    boilerplate(client, db_session, url_mapping, func_name, test)

def test_get_user(client, db_session, url_mapping):
    func_name = 'admin.get_user'
    def test(client, db_session, endpoint, **kwargs):
        import code.auth

        username, _, permissions = admin_user_table[1]
        user_id, *_ = db_session.execute('SELECT id FROM user WHERE username = :username', {'username': username}).first()
        # TEST 1: positive case

        current_endpoint = endpoint.replace('<int:id>', str(user_id))
        response = client.get(current_endpoint)
        assert response.status_code == 200 and response.is_json
        
        data = response.json
        assert username == data.get('username')
        assert data.get('permissions')
        result_permissions = [p.upper() for p in data['permissions']]
        assert permissions == ''.join(v['key'] for k, v in code.auth.permissions.items() if k in result_permissions)

        # TODO: test group membership?!        


    boilerplate(client, db_session, url_mapping, func_name, test, btest_404)

def test_register_user(client, db_session, url_mapping, csrf_token):
    func_name = 'admin.register_user'
    def test(client, db_session, endpoint, **kwargs):
        import code.auth
        kwarg_error(func_name, 'data', kwargs)

        form_data = kwargs['data']

        response = client.post(endpoint, data=form_data, follow_redirects=True)
        assert response.status_code == 200 and not response.is_json

        permission_string = ''.join(code.auth.permissions[i.upper()]['key'] for i in form_data['permissions'])
        current_password, current_permissions = db_session.execute('SELECT password, permissions FROM user WHERE username = :username', {'username': form_data['username']}).first()

        assert check_password_hash(current_password, form_data['password'])
        assert current_permissions == permission_string

        # TEST 2: duplicate user

        response = client.post(endpoint, data=form_data)
        assert response.status_code == 200 and response.is_json

        response_json = response.json
        assert response_json['STATUS'] == 'DUPLICATE'

        btest_csrf(client, db_session, endpoint, data=form_data)

    with client.session_transaction() as s:
        token = csrf_token(s)

    form_data = {
        'username': 'myNewUser',
        'password': 'Mynewpassword123',
        'password2': 'Mynewpassword123',
        'permissions': ['Gallery'],
        'token': token
    }

    boilerplate(client, db_session, url_mapping, func_name, test, data=form_data)

def test_edit_user(client, db_session, url_mapping, csrf_token):
    func_name = 'admin.edit_user'
    def test(client, db_session, endpoint, **kwargs):
        import code.auth

        kwarg_error(func_name, 'data', kwargs)

        # TEST 1: positive case

        username, _, permissions = admin_user_table[1]
        user_id, *_ = db_session.execute('SELECT id FROM user WHERE username = :username', {'username': username}).first()

        form_data = {k:v for k, v in kwargs['data'].items()}

        current_endpoint = endpoint.replace('<int:id>', str(user_id))
        response = client.post(current_endpoint, data=form_data, follow_redirects=True)
        assert response.status_code == 200 and not response.is_json

        permission_string = ''.join(code.auth.permissions[i.upper()]['key'] for i in form_data['permissions'])
        current_username, current_password, current_permissions = db_session.execute('SELECT username, password, permissions FROM user WHERE id = :id', {'id': user_id}).first()

        assert current_username == username # assert username wasn't changed by form data
        assert check_password_hash(current_password, form_data['password'])
        assert current_permissions == permission_string

        # note, this also tests fill_user functionality

        # TEST 2: mismatched password confirmation

        form_data['password2'] = "Notthesamepassword12345678"

        response = client.post(current_endpoint, data=form_data)
        assert response.status_code == 200 and response.is_json

        response_json = response.json
        assert response_json['STATUS'] == 'FAIL'

        # TEST 3: TODO: test group addition/deletion

        btest_csrf(client, db_session, current_endpoint, data=form_data)
        
    with client.session_transaction() as s:
        token = csrf_token(s)

    form_data = {
        'username': 'attemptedUsernameChange',
        'password': 'Differentpassword123',
        'password2': 'Differentpassword123',
        'permissions': ['News', 'Bulletin'],
        'token': token
    }

    boilerplate(client, db_session, url_mapping, func_name, test, btest_404, data=form_data)

def test_delete_user(client, db_session, url_mapping, csrf_token):
    func_name = 'admin.delete_user'
    def test(client, db_session, endpoint, **kwargs):
        import code.auth
        kwarg_error(func_name, 'json', kwargs)

        # TEST 1: positive case

        username, _, permissions = admin_user_table[1]
        user_id, *_ = db_session.execute('SELECT id FROM user WHERE username = :username', {'username': username}).first()

        form_data = {k:v for k, v in kwargs['json'].items()}

        current_endpoint = endpoint.replace('<int:id>', str(user_id))
        response = client.post(current_endpoint, json=form_data, follow_redirects=True)
        assert response.status_code == 200 and not response.is_json

        result = db_session.execute('SELECT username FROM user WHERE id = %d' % user_id).first() # 'safe' string injection raised exception...
        assert result is None

        # TEST 2: self deletion

        my_user_id, *_ = db_session.execute('SELECT id FROM user WHERE username = :username', {'username': admin_user_table[0][0]}).first()
        current_endpoint = endpoint.replace('<int:id>', str(my_user_id))
        response = client.post(current_endpoint, json=form_data, follow_redirects=True)
        assert response.status_code == 200 and response.is_json

        response_json = response.json
        assert response_json['STATUS'] == 'FAIL'

        result = db_session.execute('SELECT username FROM user WHERE id = %d' % my_user_id).first() # 'safe' string injection raised exception...
        assert result is not None

        # TEST 3: TODO: check user_group deletions

        btest_csrf(client, db_session, current_endpoint, json=form_data)

    with client.session_transaction() as s:
        token = csrf_token(s)

    json = {
        'token': token
    }

    boilerplate(client, db_session, url_mapping, func_name, test, btest_404, json=json)


def test_list_groups(client, db_session, url_mapping):
    func_name = 'admin.list_groups_wrapper'
    def test(client, db_session, endpoint, **kwargs):
        # TEST 1: positive case

        response = client.get(endpoint)
        assert response.status_code == 200 and response.is_json
        result_set = db_session.execute("SELECT id, title FROM groups").fetchall()
        
        names = {str(i): title for i, title in result_set}
        data = response.json
        
        assert sorted(data.get('NAMES')) == sorted(names)

    boilerplate(client, db_session, url_mapping, func_name, test)

def test_get_group(client, db_session, url_mapping):
    func_name = 'admin.get_group'
    def test(client, db_session, endpoint, **kwargs):
        import code.auth

        title, description, grouptype = admin_group_table[0]
        group_id, *_ = db_session.execute('SELECT id FROM groups WHERE title = :title', {'title': title}).first()
        # TEST 1: positive case


        current_endpoint = endpoint.replace('<int:id>', str(group_id))
        response = client.get(current_endpoint)
        assert response.status_code == 200 and response.is_json
        
        data = response.json
        assert title == data.get('title')
        assert description == data.get('description')
        assert grouptype_map[grouptype] == data.get('grouptype')

        # TODO: test user relations?
        assert 'users' in data


    boilerplate(client, db_session, url_mapping, func_name, test, btest_404)

def test_add_group(client, db_session, url_mapping, csrf_token):
    func_name = 'admin.add_group'
    def test(client, db_session, endpoint, **kwargs):
        kwarg_error(func_name, 'data', kwargs)

        form_data = kwargs['data']

        response = client.post(endpoint, data=form_data, follow_redirects=True)
        assert response.status_code == 200 and not response.is_json

        current_description, current_grouptype = db_session.execute('SELECT description, grouptype FROM groups WHERE title = :title', {'title': form_data['title']}).first()

        assert current_description == form_data['description']
        assert current_grouptype == grouptype_map[form_data['grouptype']]

        # TEST 2: duplicate group

        response = client.post(endpoint, data=form_data)
        assert response.status_code == 200 and response.is_json

        response_json = response.json
        assert response_json['STATUS'] == 'DUPLICATE'

        btest_csrf(client, db_session, endpoint, data=form_data)

    with client.session_transaction() as s:
        token = csrf_token(s)

    form_data = {
        'title': 'My New Group 3',
        'description': 'My group has some kind of description...',
        'grouptype': 2,
        'token': token
    }

    boilerplate(client, db_session, url_mapping, func_name, test, data=form_data)

def test_edit_group(client, db_session, url_mapping, csrf_token):
    func_name = 'admin.edit_group'
    def test(client, db_session, endpoint, **kwargs):
        kwarg_error(func_name, 'data', kwargs)

        # TEST 1: positive case

        title, description, grouptype = admin_group_table[0]
        group_id, *_ = db_session.execute('SELECT id FROM groups WHERE title = :title', {'title': title}).first()

        form_data = {k:v for k, v in kwargs['data'].items()}

        current_endpoint = endpoint.replace('<int:id>', str(group_id))
        response = client.post(current_endpoint, data=form_data, follow_redirects=True)
        assert response.status_code == 200 and not response.is_json

        current_title, current_description, current_grouptype = db_session.execute('SELECT title, description, grouptype FROM groups WHERE id = :id', {'id': group_id}).first()

        assert current_title == form_data['title']
        assert current_description == form_data['description']
        assert current_grouptype == grouptype_map[form_data['grouptype']]

        # TEST 2: TODO: test if flag_dirty is being called?

        btest_csrf(client, db_session, current_endpoint, data=form_data)
        
    with client.session_transaction() as s:
        token = csrf_token(s)

    form_data = {
        'title': 'Renamed Title',
        'description': "I'm now a connect!",
        'grouptype': 2,
        'token': token
    }

    boilerplate(client, db_session, url_mapping, func_name, test, btest_404, data=form_data)

def test_delete_group(client, db_session, url_mapping, csrf_token):
    func_name = 'admin.delete_group'
    def test(client, db_session, endpoint, **kwargs):
        kwarg_error(func_name, 'json', kwargs)

        # TEST 1: positive case

        title, *_ = admin_group_table[0]
        group_id, *_ = db_session.execute('SELECT id FROM groups WHERE title = :title', {'title': title}).first()

        form_data = {k:v for k, v in kwargs['json'].items()}

        current_endpoint = endpoint.replace('<int:id>', str(group_id))
        response = client.post(current_endpoint, json=form_data, follow_redirects=True)
        assert response.status_code == 200 and not response.is_json

        result = db_session.execute('SELECT title FROM groups WHERE id = %d' % group_id).first() # 'safe' string injection raised exception...
        assert result is None

        # TODO: check if user_group deletions are happening

        btest_csrf(client, db_session, current_endpoint, json=form_data)

    with client.session_transaction() as s:
        token = csrf_token(s)

    json = {
        'token': token
    }

    boilerplate(client, db_session, url_mapping, func_name, test, btest_404, json=json)

# def test_activity(client, db_session):
#     pass