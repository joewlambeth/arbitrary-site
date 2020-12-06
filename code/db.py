from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from flask import Flask, current_app
from flask.cli import with_appcontext
import click

db_config = current_app.config['DB']

current_db = 'code' if not current_app.config.get('TESTING') else 'test'

if not db_config.get('URI'):
    engine = create_engine("mysql+pymysql://%s:%s@%s/%s" % (db_config['USER'], db_config['PASS'], db_config['HOST'], current_db) )
else:
    engine = create_engine("mysql+pymysql://%s:%s@/%s?unix_socket=%s" % (db_config['USER'], db_config['PASS'], current_db, db_config['URI']))
session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = session.query_property()

def init_db():
    import code.model
    session.commit()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(bind=engine)

@click.command('init-db')
@with_appcontext
def init_db_command():
    # TODO: this needs to consult fs_handler as well...
    init_db()
    click.echo('Initialized the database.')

@click.command('update-db')
@with_appcontext
def update_db():
    import code.model
    Base.metadata.create_all(bind=engine)
    click.echo('Updated the database.')


def close_db(exception=None):
    session.remove()

def get_db():
    return session

def commit():
    get_db().commit()

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

