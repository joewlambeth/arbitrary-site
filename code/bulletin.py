from flask import Blueprint, jsonify, Response, abort, request, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from .db import get_db, commit
from .auth import login_required, validate_token, check_permissions
from .error import json_responses, JsonResponseError
from .model import Bulletin

bp = Blueprint('bulletin', __name__, url_prefix='/bulletin')
bulletin_permission = 'BULLETIN'

@bp.route('/<int:page>', methods=['POST'])
def list(page):
    entries = 5
    bulletins = Bulletin.query.order_by(Bulletin.created).all()[::-1][(page - 1) * entries: page * entries]
    if len(bulletins) == 0 and page != 1:
        return list(1)
    json = {'posts': [{k:v for k,v in b.__dict__.items() if k in ['link', 'title']} for b in bulletins], 
            'next_page': (get_count() - (page * entries)) > 0 }
    if check_permissions(bulletin_permission) and page == 1:
        json['editable'] = True
    return jsonify(json)

@bp.route('/<string:link>', methods=['GET'])
def view(link):
    pdf = Bulletin.query.filter(Bulletin.link == link).all()
    if pdf is None:
        abort(404)
    
    bytes = current_app.fs_handler.load("bulletin/" + link)    
    response = Response(bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=%s' % link
    return response

@bp.route('/upload', methods=['POST'])
@login_required(bulletin_permission)
def upload():
    db = get_db()
    try:
        if not validate_token(request.form.get('token')):
            raise JsonResponseError('ERROR')
        file = request.files.get('file')
        if not file or file.filename == '':
            raise JsonResponseError('CANCEL')
        if not file.filename.split('.')[-1].lower() == 'pdf':
            raise JsonResponseError("INVALID", "Filename", file.filename)
        elif not request.form['title'] or request.form['title'] == '':
            raise JsonResponseError("INVALID", "Title", request.form['title'])
        bulletin = Bulletin.query.filter(Bulletin.title == request.form['title']).first()
        if bulletin is not None:
            raise JsonResponseError("DUPLICATE", "Title", request.form['title'])
        filename = secure_filename(file.filename)
        bulletins = Bulletin.query.filter(Bulletin.link.like("%{}%".format(filename[:filename.rfind('.')])))

        if bulletins.count() > 0:
            file_parts = filename.split('.')
            filename = file_parts[0] + f"({bulletins.count()})." + '.'.join(file_parts[1:])

        
        
        bulletin = Bulletin(request.form['title'], filename)
        db.add(bulletin)
        current_app.fs_handler.save("bulletin/" + filename, file.read())
        commit()
        return redirect(url_for('news.index'))
    # TODO: handle db flaws
    except JsonResponseError as e:
        db.rollback()
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })

@bp.route('/delete', methods=('POST',))
@login_required(bulletin_permission)
def delete():
    db = get_db()
    try:
        links = request.json.get('links')
        if links:
            if not validate_token(request.json.get('token')):
                raise JsonResponseError("ERROR")
            bulletins = Bulletin.query.filter(Bulletin.link.in_(links))
            
            for bulletin in bulletins:
                db.delete(bulletin)
                current_app.fs_handler.delete("bulletin/" + bulletin.link)
                commit()

            return redirect(url_for("news.index"))
        # TODO: handle DB exception
    except JsonResponseError as e:
        db.rollback()
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })
                
    
    
def get_count():
    return Bulletin.query.count()