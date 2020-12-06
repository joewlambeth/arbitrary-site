from flask import Blueprint, render_template, request, abort
from .model import Group
from .db import get_db

bp = Blueprint('connect', __name__)

entries = 8
dirty = True
names = {'groups':[], 'connect':[]}
full_names = {'groups': 'Ministries & Groups', 'connect': 'Serve & Connect'}

def flag_dirty():
    global dirty
    dirty = True

def fetch_all():
    global names, dirty
    if dirty:
        all_groups = Group.query.with_entities(Group.id, Group.title, Group.grouptype).all()
        names['connect'] = [(link, name) for link, name, group in all_groups if group.name == 'connect']
        names['groups'] = [(link, name) for link, name, group in all_groups if group.name == 'groups']
        dirty = False
        print("Cleaned cache!")
    return names

@bp.route("/connect/")
def index_connect():
    return index('connect')

@bp.route("/groups/")
def index_groups():
    return index('groups')

def index(group_type):
    global entries
    page = int(request.args.get('page') or 1)
    groups = Group.query.filter(Group.grouptype == group_type).all()[::-1][(page - 1) * entries :(page) * entries]
    if len(groups) == 0 and page != 1:
        abort(404)
    elif len(groups) == 0:
        return render_template('connect/index.j2')
    return render_template('connect/index.j2', groups=groups, active_menu=full_names[group_type], grouptype=group_type, page=page, entries=entries)

@bp.route("/connect/<int:id>")
def view_connect(id):
    return view("connect", id)

@bp.route("/groups/<int:id>")
def view_groups(id):
    return view("groups", id)

def view(group_type, id):
    previous = int(request.args.get('previous') or 1)
    group = Group.query.filter(Group.id == id and Group.grouptype == group_type).first()
    group.popularity += 1
    get_db().flush()
    return render_template("connect/view.j2", previous=previous, group=group, active_menu=full_names[group_type], grouptype=group_type)