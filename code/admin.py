from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, abort
from werkzeug.security import generate_password_hash
from sqlalchemy import event, inspect
from .auth import valid_username, valid_password, permissions, login_required, validate_token
from .connect import flag_dirty
from .db import get_db, commit
from .model import User, UserGroup, Group, Activity
from .error import json_responses, JsonResponseError, FormRequirementError, valid_form_entry

bp = Blueprint('admin', __name__, url_prefix="/admin", template_folder="admin")

@bp.route("/", methods=('GET', 'POST'))
@login_required("ADMIN")
def index():
    if request.method == 'POST':
        return jsonify({
            'permissions': {k.capitalize():[c.capitalize() for c in v['children']] if v.get('children') else {} for k, v in permissions.items()},
            'groups': list_groups()
        })
    else:    
        return render_template("admin/admin.j2")

@bp.route("/user", methods=("GET", ))
@login_required("ADMIN")
def list_users():
    users = User.query.with_entities(User.id, User.username).all()
    users = {u[0]: u[1] for u in users}
    return jsonify({
        'NAMES': users
    })

@bp.route("/user/<int:id>", methods=("GET", ))
@login_required("ADMIN")
def get_user(id):
    user = User.query.filter(User.id == id).first()
    if user is None:
        abort(404)
    flipped_permissions = {v['key']:k for k, v in permissions.items()}
    group_ids = UserGroup.query.with_entities(UserGroup.group_id).filter(UserGroup.user_id == id).all()
    return jsonify({
        'username': user.username,
        'permissions': [flipped_permissions[p].capitalize() for p in user.permissions],
        'groups': [g.group_id for g in group_ids]
    })

@bp.route("/user/register", methods=("POST", ))
@login_required("ADMIN")
def register_user():
    try:
        if not request.form:
            abort(400)
        if not validate_token(request.form.get('token')):
            raise JsonResponseError("ERROR")
        username = request.form['username']
        if User.query.filter(User.username == username).scalar():
            raise JsonResponseError("DUPLICATE", "Username", username)

        try:
            valid_form_entry('user', 'username', username)
            user = User(username)
            fill_user(user, True)
            
            # reference is bad on old user, have to requery for it
            user = User.query.filter(User.username == username).first()

            return redirect(url_for('admin.index'))
        except FormRequirementError as e:
            raise JsonResponseError("FAIL", desc=e.description)

        
    except JsonResponseError as e:
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })

@bp.route("/user/<int:id>/edit", methods=("POST", ))
@login_required("ADMIN")
def edit_user(id):
    try:
        if not request.form:
            abort(400)
        if not validate_token(request.form.get('token')):
            raise JsonResponseError('ERROR')
        user = User.query.filter(User.id == id).first()

        if user is None:
            abort(404)

        fill_user(user, False)

        return redirect(url_for("admin.index"))
    except JsonResponseError as e:
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })

@bp.route('/user/<int:id>/delete', methods=("POST", ))
@login_required("ADMIN")
def delete_user(id):
    db = get_db()
    try:
        if not request.json:
            abort(400)
        if not validate_token(request.json.get('token')):
            raise JsonResponseError('ERROR')
        user = User.query.filter(User.id == id).first()

        if not user:
            abort(404)

        if user.username == session.get('username'):
            # TODO: this should be handled client side as well
            raise JsonResponseError('FAIL', desc="You cannot delete yourself!")

        db.delete(user)
        commit()

        return redirect(url_for("admin.index"))
    except JsonResponseError as e:
        db.rollback()
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })
    except Exception as e:
        db.rollback()
        raise e


def fill_user(user, fresh):
    try:
        password = request.form['password']
        if password != request.form['password2']:
            raise JsonResponseError("FAIL", desc="Passwords do not match")

        if password != '' or fresh:
            try:
                valid_form_entry('user', 'password', password)
                user.password = generate_password_hash(password)
            except FormRequirementError as e:
                raise JsonResponseError("FAIL", desc=e.description)
        
        user.permissions = ''
        for permission in request.form.getlist('permissions'):
            user.permissions += permissions[permission.upper()]['key']
        
        user_groups = {g.id: g for g in user.groups}
        form_groups = request.form.getlist('groups')
        for form_group_id in form_groups:
            if form_group_id not in user_groups.keys():
                group = Group.query.get(form_group_id)
                user.groups.append(group)

        for user_group_id in user_groups.keys():
            if user_group_id not in form_groups:
                # group = Group.query.get(user_group_id)
                user.groups.remove(user_groups[user_group_id])

        if fresh:
            get_db().add(user)
        commit()
    except Exception as e:
        get_db().rollback()
        raise e

@bp.route("/group", methods=("GET", ))
@login_required("ADMIN")
def list_groups_wrapper():
    groups = Group.query.with_entities(Group.id, Group.title).all()
    groups = {g[0]: g[1] for g in groups}
    return jsonify({
        'NAMES': list_groups()
    })

def list_groups():
    groups = Group.query.with_entities(Group.id, Group.title).all()
    return {g.id: g.title for g in groups}


@bp.route("/group/<int:id>", methods=("GET", ))
@login_required("ADMIN")
def get_group(id):
    group = Group.query.filter(Group.id == id).first()
    if not group:
        abort(404)
    # TODO: do this with proper joins
    user_ids = UserGroup.query.with_entities(UserGroup.user_id).filter(UserGroup.group_id == id).all()
    user_names = User.query.with_entities(User.username).filter(User.id.in_([x.user_id for x in user_ids])).all()
    return jsonify({
        'title': group.title,
        'description': group.description,
        'users': [x.username for x in user_names],
        'grouptype': group.grouptype.name
    })


@bp.route("/group/add", methods=("POST", ))
@login_required("ADMIN")
def add_group():
    try:
        if not request.form:
            abort(400)
        if not validate_token(request.form.get('token')):
            raise JsonResponseError("ERROR")
        title = request.form['title']
        if Group.query.filter(Group.title == title).scalar():
            raise JsonResponseError("DUPLICATE", "Group Title", title)

        try:
            # TODO: add rules for group names?
            group = Group(title)
            fill_group(group, True)

            return redirect(url_for("admin.index"))
        except FormRequirementError as e:
            raise JsonResponseError("FAIL", desc=e.description)

        
    except JsonResponseError as e:
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })


@bp.route("/group/<int:id>/edit", methods=("POST", ))
@login_required("ADMIN")
def edit_group(id):
    try:
        if not request.form:
            abort(400)
        if not validate_token(request.form.get('token')):
            raise JsonResponseError('ERROR')
        group = Group.query.filter(Group.id == id).first()
        if not group:
            abort(404)

        group.title = request.form['title']
        fill_group(group, False)

        return redirect(url_for("admin.index"))
    except JsonResponseError as e:
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })


@bp.route("/group/<int:id>/delete", methods=("POST", ))
@login_required("ADMIN")
def delete_group(id):
    db = get_db()
    try:
        if not request.json:
            abort(400)
        if not validate_token(request.json.get('token')):
            raise JsonResponseError('ERROR')

        user_groups = UserGroup.query.filter(UserGroup.group_id == id).all()
        group = Group.query.filter(Group.id == id).first()

        if not group:
            abort(404)

        for ug in user_groups:
            db.delete(ug)
        db.delete(group)
        commit()

        return redirect(url_for("admin.index"))
    except JsonResponseError as e:
        db.rollback()
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })
    except Exception as e:
        db.rollback()
        raise e


def fill_group(group, fresh):
    try:
        flag_dirty()
        group.description = request.form['description']
        group.grouptype = request.form['grouptype']

        if fresh:
            get_db().add(group)
        commit()
    except Exception as e:
        get_db().rollback()
        raise e

@bp.route("/activity", methods=("POST",))
@login_required("ADMIN")
def list_activities():
    activities = Activity.query.all()
    activities = [str(activity) for activity in activities]
    return jsonify(activities)

activities = dict()

@event.listens_for(get_db(), 'before_flush')
def cache_changes(s, flush_context, _):
    global activities
    
    db = get_db()
    activities['added'] = [obj for obj in db.new if obj.__tablename__ != 'activity']
    activities['edited'] = [obj for obj in db.dirty if db.is_modified(obj)]
    activities['deleted'] = db.deleted

@event.listens_for(get_db(), 'after_flush')
def log_changes(s, flush_context):
    global activities
    if any(map(lambda x: len(activities[x]) > 0, activities)):
        username = session.get('username') if session else 'root' or 'root'
        db = get_db()
        all_activities = list()

        for activity_type, activity_set in activities.items():
            for obj in activity_set:
                activity = None
                if activity_type == 'edited':
                    state = inspect(obj)
                    for attr in state.attrs:
                        hist = attr.load_history()
                        if hist.has_changes():
                            all_activities.append(Activity(username, activity_type, obj.__repr__(), attr.key))
                else:
                    all_activities.append(Activity(username, activity_type, obj.__repr__()))
        
        
        for activity in all_activities:
            db.add(activity)
            print(activity.__str__())
            
        activities = dict()
            