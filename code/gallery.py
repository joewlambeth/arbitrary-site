import io
from PIL import Image
from flask import Blueprint, request, current_app, abort, render_template, jsonify, Response, redirect, url_for
from werkzeug.utils import secure_filename
from .auth import login_required, check_permissions, validate_token
from .model import Gallery
from .db import get_db, commit
from .error import JsonResponseError

bp = Blueprint('gallery', __name__, url_prefix='/gallery')
acceptable_images = ('png', 'bmp', 'gif', 'jpg', 'jpeg')
preview_size = (256, 256)

# TODO: at least 2 transactions per load? that's nasty!
# ditching pagination for now...
@bp.route('/', methods=('GET', 'POST'))
def index():
    if request.method == 'POST':
        entries = current_app.config['GALLERY_QUERY_LIMIT']
        page = int(request.args.get('page') or 1)
        gallery = [x[0] for x in Gallery.query.with_entities(Gallery.link).all()[::-1]] #[(page - 1) * entries: page * entries]]
        if len(gallery) == 0 and page != 1:
            abort(404)
        json = {'gallery': gallery, 
                'next_page': (get_count() - (page * entries)) > 0 }
        if check_permissions("GALLERY") and page == 1:
            json['editable'] = True
        return jsonify(json)
    else:
        return render_template('gallery.j2', active_menu="Gallery")

@bp.route('view_preview/<string:link>')
def view_preview(link):
    return view_image(link, True)

@bp.route('view_full/<string:link>')
def view_full(link):
    return view_image(link, False)

def view_image(link, preview):
    img = Gallery.query.filter(Gallery.link == link).first()
    if img is None:
        abort(404)
    
    image_type = 'preview/' if preview else 'full/'

    print("gallery/" + image_type + link)

    bytes = current_app.fs_handler.load("gallery/" + image_type + link)    
    response = Response(bytes)
    response.headers['Content-Type'] = 'image/' + link.split('.')[-1]
    return response

@bp.route("info/<string:link>")
def info(link):
    img = Gallery.query.filter(Gallery.link == link).first()
    if img is None:
        abort(404)

    return jsonify({
        'title': img.title,
        'created': str(img.created)
    })


@login_required("GALLERY")
@bp.route('/upload', methods=("POST",))
def upload():
    db = get_db()
    try:
        if not validate_token(request.form.get('token')):
            raise JsonResponseError('ERROR')
        file = request.files.get('file')
        if not file or file.filename == '':
            raise JsonResponseError('CANCEL')
        if not file.filename.split('.')[-1].lower() in acceptable_images:
            raise JsonResponseError("INVALID", "Filename", file.filename)
        elif not request.form['title'] or request.form['title'] == '':
            raise JsonResponseError("INVALID", "Title", request.form['title'])
        img = Gallery.query.filter(Gallery.title == request.form['title']).first()
        if img is not None:
            raise JsonResponseError("DUPLICATE", "Title", request.form['title'])
        filename = secure_filename(file.filename)
        images = Gallery.query.filter(Gallery.link.like("%{}%".format(filename[:filename.rfind('.')])))

        if images.count() > 0:
            file_parts = filename.split('.')
            filename = file_parts[0] + f"({images.count()})." + '.'.join(file_parts[1:])

        
        img = Gallery(request.form['title'], filename)
        db.add(img)
        img_bytes = file.read()

        # creating reduced image for lazy loading
        inbuffer = io.BytesIO(img_bytes)
        
        fp_img = Image.open(inbuffer)
        width, height = fp_img.size
        
        difference = (width - height) / 2
        if difference > 0:
            dimensions = (difference, 0, width - difference, height)
        else:
            dimensions = (0, difference, width, height - difference)

        img_crop = fp_img.crop(dimensions)
        img_resized = img_crop.resize(preview_size)
        outbuffer = io.BytesIO()
        ext = file.filename.split('.')[-1].lower()
        
        # welp, what can ya do...
        if ext == 'jpg':
            ext = 'jpeg'
        img_resized.save(outbuffer, format = ext)
        resized_bytes = outbuffer.getvalue()

        current_app.fs_handler.save("gallery/full/" + filename, img_bytes)
        current_app.fs_handler.save("gallery/preview/" + filename, resized_bytes)
        commit()
        return redirect(url_for('gallery.index'))
    # TODO: handle db flaws
    except JsonResponseError as e:
        db.rollback()
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })

@bp.route('/edit/<string:link>', methods=("POST",))
@login_required("GALLERY")
def edit(link):
    db = get_db()
    try:
        if not validate_token(request.json.get('token')):
            raise JsonResponseError('ERROR')
        elif not request.json['title'] or request.json['title'] == '':
            raise JsonResponseError("INVALID", "Title", request.form['title'])
        img = Gallery.query.filter(Gallery.title == request.json['title'] and Gallery.link != link).first()
        if img is not None:
            raise JsonResponseError("DUPLICATE", "Title", request.json['title'])
        

        img = Gallery.query.filter(Gallery.link == link).first()
        img.title = request.json['title']
        commit()
        return redirect(url_for("gallery.index"))
    # TODO: handle db flaws
    except JsonResponseError as e:
        db.rollback()
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })


def fill_img():
    pass

@bp.route('/delete/<string:link>', methods=("POST",))
@login_required("GALLERY")
def delete(link):
    db = get_db()
    try:
        if not validate_token(request.json.get('token')):
            raise JsonResponseError("ERROR")
        image = Gallery.query.filter(Gallery.link == link).first()
        if not image:
            abort(404)
        
        db.delete(image)
        current_app.fs_handler.delete("gallery/full/" + image.link)
        current_app.fs_handler.delete("gallery/preview/" + image.link)
        commit()
        return redirect(url_for("gallery.index"))
        # TODO: handle DB exception
    except JsonResponseError as e:
        db.rollback()
        return jsonify({
            'STATUS': e.name,
            'DESC': e.description
        })

def get_count():
    return Gallery.query.count()