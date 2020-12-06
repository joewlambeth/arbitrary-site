import os
import os.path

from flask import Flask, request, render_template, g

blueprints = ['news', 'gallery', 'serve_&_connect', 'ministries_&_groups']

navigation_bar = {
    'About Us': {'endpoint':False, 'children': ('Mission Statement', 'Leadership and Staff', 'Faith in Action', 'Contact Us')},
    'Serve & Connect': {'endpoint': 'connect/'}, #('Music and Arts', 'Fellowship', 'Education'),
    'Ministries & Groups': {'endpoint': 'groups/'}, # ('Volunteering', 'Food Pantry', 'Prayer Requests'),
    'Gallery': {},
    'News': {},
    'Early Learning Center': {'endpoint': False, 'children': ('Staff', 'Class Schedules', 'Contact ELC')},
}

menu_translations = {
    'Serve & Connect': 'Connect',
    'Ministries & Groups': 'Groups'
}

def create_menu_item(x):
    return snake_case(x)

def preprocess_navbar(callables):
    for menu_item, items in navigation_bar.items():
        if 'endpoint' not in items:
            items['endpoint'] = create_menu_item(menu_item)
        if menu_item in callables:
            items['func'] = callables[menu_item]

def snake_case(x):
    y = x.lower()
    y = y.replace(' ', '_')
    return y


def render_construction():
    return render_template('under_construction.j2')


def func_renderer(menu_item, sub_menu_item=None):
    translated_menu = create_menu_item(menu_item)
    translated_submenu = create_menu_item(sub_menu_item) if sub_menu_item else None
    if sub_menu_item and translated_submenu + '.j2' in os.listdir(os.path.dirname(os.path.abspath(__file__)) + '/templates'):
        return lambda: render_template(translated_submenu + '.j2', active_menu=menu_item)
    elif translated_menu + '.j2' in os.listdir(os.path.dirname(os.path.abspath(__file__)) + '/templates'):
        return lambda: render_template(translated_menu + '.j2', active_menu=menu_item)
    else:
        return render_construction


def error_renderer(error_code):
    return lambda x: (render_template('error.j2', error=error_code), error_code)

def create_app(test_config=None):
    app = Flask(__name__)
    # if not test_config:
    #     app.config.from_json('config.json')
    # else:
    #     app.config.from_mapping(test_config)

    app.config.from_json('config.json')
    if test_config:
        app.config.update(test_config)
    
    with app.app_context():
        import code.db as db
        db.init_app(app)
        from code.fs import LocalFileHandler, GCloudFileHandler

    fs_handlers = {
        'LOCAL': LocalFileHandler,
        'GCLOUD': GCloudFileHandler
    }

    if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ and app.config['FS'].get('CREDENTIALS') is not None:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = app.config['FS']['CREDENTIALS']

    try:
        with app.app_context():
            app.fs_handler = fs_handlers[app.config['FS']['TYPE']](app.config['FS']['DESTINATION'])
    except Exception:
        print("Unable to load file system. Oh well")

    import code.auth, code.news, code.bulletin, code.admin, code.connect, code.gallery

    app.register_blueprint(code.auth.bp)
    app.register_blueprint(code.news.bp)
    app.register_blueprint(code.bulletin.bp)
    app.register_blueprint(code.admin.bp)
    app.register_blueprint(code.connect.bp)
    app.register_blueprint(code.gallery.bp)

    app.cli.add_command(code.auth.register_admin)
    app.cli.add_command(code.db.update_db)

    preprocess_navbar({'Serve & Connect': lambda: [('connect/' + str(link), name) for link, name in code.connect.fetch_all()['connect']], 
                       'Ministries & Groups': lambda: [('groups/' + str(link), name) for link, name in code.connect.fetch_all()['groups']]
    })

    nav_bar = dict()
    for menu_item, items in navigation_bar.items():
        if items['endpoint'] != False:
            if create_menu_item(menu_item) in blueprints or func_renderer(menu_item) != render_construction:
                nav_bar[menu_item] = navigation_bar[menu_item]
            else:
                print(menu_item, "is under construction")
        sub_menu = items.get('children')
        if sub_menu is not None:
            for sub_menu_item in sub_menu:
                if func_renderer(menu_item, sub_menu_item) != render_construction:
                    if menu_item not in nav_bar:
                        nav_bar[menu_item] = dict()
                        nav_bar[menu_item]['endpoint'] = navigation_bar[menu_item]['endpoint']
                        nav_bar[menu_item]['children'] = list()
                    nav_bar[menu_item]['children'].append(sub_menu_item)
                else:
                    print(menu_item, ":", sub_menu_item, "is under construction")

    nav_bar = nav_bar if not app.config['DEBUG'] else navigation_bar

    app.jinja_env.globals.update(create_menu_item=create_menu_item)
    app.jinja_env.globals.update(navigation_bar=nav_bar)
    app.jinja_env.globals.update(get_count=code.news.get_count)
    app.jinja_env.globals.update(get_pages=code.news.get_pages)
    app.jinja_env.globals.update(check_permissions=code.auth.check_permissions)
    import code.model
    app.jinja_env.globals.update(GroupEnum=code.model.GroupEnum)

    for menu_item, items in nav_bar.items():
        if items['endpoint'] != False:
            app.add_url_rule('/' + items['endpoint'], create_menu_item(menu_item), func_renderer(menu_item))
        sub_menu = items.get('children')
        if sub_menu is not None:
            for sub_menu_item in sub_menu:
                app.add_url_rule('/' + create_menu_item(sub_menu_item), create_menu_item(sub_menu_item),
                                 func_renderer(menu_item, sub_menu_item))

    @app.route("/")
    def index():
        return render_template('index.j2', active_menu="Home")

    @app.route("/cookie_policy")
    def cookie_policy():
        return render_template('cookie_policy.j2')

    for error in (400, 403, 404, 500, 502):
        app.register_error_handler(error, error_renderer(error))
    
    import code.error

    code.error.build_form_regexes()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8080)
