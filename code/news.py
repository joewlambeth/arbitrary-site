from flask import Blueprint, render_template, request, url_for, redirect, flash, abort, session, jsonify, current_app
from code.auth import login_required, validate_token, generate_token, check_permissions
from code.db import get_db, commit
from code.model import NewsPost, NewspostGroup, Group, GroupEnum, Tag, NewspostTag, GalleryTag
from sqlalchemy import desc

bp = Blueprint('news', __name__, url_prefix="/news", template_folder="news")

@bp.route("/", methods=('GET', 'POST'))
def index():
    entries = current_app.config["NEWS_QUERY_LIMIT"]
    if request.method == 'POST':
        groups_and_tags = fetch_groups_and_tags()
        return jsonify(groups_and_tags)

    filtered=False
    page = int(request.args.get('page') or 1)
    query = NewsPost.query.order_by(NewsPost.created)
    if request.args.get('group'):
        group_id = int(request.args['group'])
        if group_id == -1:
            return redirect(request.path)
        newspostgroups = NewspostGroup.query.with_entities(NewspostGroup.news_id).filter(NewspostGroup.group_id == group_id).all()
        query = query.filter(NewsPost.id.in_([n.news_id for n in newspostgroups]))
        filtered = True
    elif request.args.get('tag'):
        tag_id = int(request.args['tag'])
        if tag_id == -1:
            return redirect(request.path)
        newsposttags = NewspostTag.query.with_entities(NewspostTag.news_id).filter(NewspostTag.tag_id == tag_id).all()
        query = query.filter(NewsPost.id.in_([n.news_id for n in newsposttags]))
        filtered = True

    posts = query.all()[::-1][(page - 1) * entries :(page) * entries]
    if len(posts) == 0 and page != 1:
        abort(404)
    elif len(posts) == 0:
        return render_template('news/index.j2')
    return render_template('news/index.j2', posts=posts, filtered=filtered, active_menu="News", page=page, entries=entries)

def fetch_groups_and_tags():
    tags = Tag.query.all()
    tags_dict = {t.id: t.tag for t in tags}

    groups = Group.query.all()
    group_list = [g for g in groups if g.grouptype == GroupEnum.groups]
    connect_list = [c for c in groups if c.grouptype == GroupEnum.connect]

    groups_dict = {'groups': {g.id: g.title for g in group_list}, 'connect': {c.id: c.title for c in connect_list}}
    return {
        'tags': tags_dict,
        'groups': groups_dict
    }

@bp.route("/<int:id>", methods=('GET', 'POST'))
def view(id):
    previous = int(request.args.get('previous') or 1)
    post = NewsPost.query.filter(NewsPost.id == id).first()
    if not post:
        abort(404)
    if request.method == 'GET':
        return render_template('news/view.j2', previous=previous, post=post, active_menu="News")
    else:
        tag = post.tag[0].id if len(post.tag) > 0 else -1
        group = post.group[0].id if len(post.group) else -1
        return jsonify({
            **fetch_groups_and_tags(),
            'title': post.title,
            'body': post.body,
            'tag': tag,
            'group': group
        })

@bp.route("/add", methods=('GET', 'POST'))
@login_required('NEWS')
def add():
    if request.method == 'POST':
        return fill_post()
    return render_template('news/add.j2', post=None, active_menu="News", token=generate_token())


@bp.route("/<int:id>/edit", methods=('GET', 'POST'))
@login_required('NEWS')
def edit(id):
    post = NewsPost.query.filter(NewsPost.id == id).first()

    if post is None:
        abort(404)

    if request.method == 'POST':
       return fill_post(post)

    return render_template('news/add.j2', post=post, active_menu="News", token=generate_token())

def fill_post(post=None):
    if not validate_token(request.form.get('token')):
        error = "An error has occurred."
    title = request.form['title']
    body = request.form['body']
    tag = None
    group = None

    if request.form.get('newtag') and request.form['newtag'] != '':
        tag_name = request.form['newtag']
        tag = Tag.query.filter(Tag.tag == tag_name).first()
        if not tag:
            tag = Tag(tag_name)
            get_db().add(tag)
            get_db().flush()
        tag_id = tag.id
    elif request.form.get('tag'):
        tag_id = request.form['tag']
        if tag_id != -1:
            tag = Tag.query.filter(Tag.id == tag_id).first()
    elif request.form.get('group'):
        group = Group.query.filter(Group.id == request.form['group']).first()

    # TODO: this is poor error handling
    error = None
    if not title:
        error = "Title is required"
    if not body:
        error = "Body is required"

    if error is not None:
        flash(error)
    else:
        if not post:
            post = NewsPost(title, body)
            post.group = [group] if group else []
            post.tag = [tag] if tag else []
            get_db().add(post)
        else:
            if len(post.tag) > 0 and post.tag[0] != tag:
                check_tag_cleanup(post)
            if tag:
                post.tag.append(tag)
                
            post.title = title
            post.body = body
            if len(post.group) > 0 and post.group[0] != group:
                post.group.remove(post.group[0])
            if group:
                post.group.append(group)
        
        commit()
        return redirect(url_for('news.index'))
    return render_template('news/add.j2', post=post, active_menu="News", token=generate_token())

@login_required('NEWS')
@bp.route("/<int:id>/delete", methods=("POST",))
def delete(id):
    if validate_token(request.form.get('token')):
        post = NewsPost.query.filter(NewsPost.id == id).first()

        if post is None:
            abort(404)
            
        check_tag_cleanup(post)

        db = get_db()
        db.delete(post)
        commit()

    return redirect((url_for('news.index')))

def check_tag_cleanup(post):
    # yes, i'm aware this function doesn't commit changes to db
    # this is deliberate, and meant to be called from another function that WILL commit
    # in the event that the parent transaction rolls back, so will this
    
    if len(post.tag) > 0:
        old_tag = post.tag[0]
        post.tag.remove(old_tag)

        newspost_tags = NewspostTag.query.filter(NewspostTag.tag_id == old_tag.id).all()
        gallery_tags = GalleryTag.query.filter(GalleryTag.tag_id == old_tag.id).all()
        
        # i'm assuming this is read committed??
        if len(gallery_tags) == 0 and len(newspost_tags) == 1 and newspost_tags[0].news_id == post.id:
            tag = Tag.query.filter(Tag.id == newspost_tags[0].tag_id).first()
            if tag:
                get_db().delete(tag)
        

    

def get_count():
    return NewsPost.query.count()

def get_pages(page):
    entries = current_app.config["NEWS_QUERY_LIMIT"]
    page_count = int(round(get_count() / entries))
    seek = 6
    if (page_count < seek * 2):
        return set(range(1, page_count + 1))
    else:
        return {(p if p <= page_count else (page - seek) - (p - page_count) ) if p > 0 else -p + page + seek for p in range(page - seek + 2, page + seek)}
