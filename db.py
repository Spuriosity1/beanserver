import sqlite3
from flask import g, current_app
import os
import click

#DB construction
def init_db():
    with current_app.open_resorce('create_database.sql') as f:
        sqlite3.connect(cfg['PRIMARYDB']).executescript(f.read().decode('utf8'))
        sqlite3.connect(cfg['SECONDARYDB']).executescript(f.read().decode('utf8'))

@click.command('init-db')
def init_db_command():
    '''Clear existing data and create new tables.'''
    if open_db() is not None:
        proceed = click.confirm(f'''WARNING
This operation will delete existing databases located at
{current_app.config['PRIMARYDB']} {current_app.config['SECONDARYDB']}
Are you sure you want to proceed?''', abort=True)
    init_db()
    click.echo('Created new databases.')

def init_app(app):
    app.teardown_appcontext(close_db)
    print("register command")
    app.cli.add_command(init_db_command)

def open_db():
    cfg =current_app.config
    g.db = None
    try:
        if (os.path.isfile(cfg['PRIMARYDB'])):
            g.db = sqlite3.connect(cfg['PRIMARYDB'])
            g.db_idx = 1
        elif (os.path.isfile(cfg['SECONDARYDB'])):
            g.db = sqlite3.connect(cfg['SECONDARYDB'])
            g.db_idx = 2
    except sqlite3.OperationalError:
        return None
    
    return g.db

def close_db(_):
    db = g.pop('db',None)
    if db is not None:
        db.close()


        
