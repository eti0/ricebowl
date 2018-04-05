#!/usr/bin/env python3
import os
import uuid
import random
import sqlite3
from flask import *
from flaskext.markdown import Markdown
from flask_uploads import *

# Admin token
admin_token = str(uuid.uuid4())
print("Admin token:", admin_token)

# Flask
app = Flask(__name__)
app.jinja_options = { 'trim_blocks': True, 'lstrip_blocks': True }
app.secret_key = str(uuid.uuid4())

# Markdown
Markdown(app)

# Uploads
screenshots = UploadSet('screenshots', ('jpg', 'jpeg', 'png', 'bmp'))
app.config['UPLOADED_SCREENSHOTS_DEST'] = os.path.join(app.root_path, 'static/screenshots')
configure_uploads(app, screenshots)
patch_request_class(app, 8 * 1024 * 1024)

# Database

DATABASE = os.path.join(app.root_path, 'db.sqlite')

def get_db():
    if not 'db' in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.execute('create table if not exists user(key text primary key, nickname text, screenshot text, vote text)')
    return g.db

@app.teardown_appcontext
def close_connection(e):
    if 'db' in g:
        g.db.close()

# Routing

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        key = request.form.get('key')
        user = get_db().execute('select screenshot from user where key = ?', (key,)).fetchone()
        if not user:
            message, success = "Wrong key.", False
        else:
            old_screenshot, = user
            try:
                screenshot = screenshots.save(request.files['screenshot'])
            except:
                message, success = "Invalid file.", False
            else:
                if old_screenshot:
                    try:
                        os.remove(screenshots.path(old_screenshot))
                    except:
                        pass
                with get_db() as db:
                    db.execute('update user set screenshot = ? where key = ?', (screenshot, key))
                message, success = "Uploaded!", True
        if 'from_form' in request.form:
            flash(message, success)
            return redirect(url_for('vote' if success else 'submit'))
        else:
            return message + '\n'
    else:
        return render_template('submit.html', title='submit')

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if request.method == 'POST':
        key = request.form.get('key')
        vote_for = request.form.get('vote')
        user = get_db().execute('select nickname from user where key = ?', (key,)).fetchone()
        if not user:
            message, success = "Wrong key.", False
        else:
            nickname, = user
            if nickname == vote_for:
                message, success = "You can't vote for yourself.", False
            elif vote_for and not get_db().execute('select nickname from user where nickname = ?', (vote_for,)).fetchone():
                message, success = "Wrong nickname: %s" % vote_for, False
            else:
                with get_db() as db:
                    db.execute('update user set vote = ? where key = ?', (vote_for, key))
                if vote_for:
                    message, success = "You voted for: %s" % vote_for, True
                else:
                    message, success = "Your vote has been removed.", True
        return message + '\n'
    else:
        users = []
        query = 'select nickname, screenshot, (select count(*) from user as voter where user.nickname = voter.vote) as votes from user order by votes desc, random()'
        for nickname, screenshot, votes in get_db().execute(query):
            if screenshot and os.path.isfile(screenshots.path(screenshot)):
                users.append({
                    'nickname': nickname,
                    'screenshot': screenshots.url(screenshot),
                    'votes': votes
                })
        return render_template('vote.html', title='vote', users=users)

@app.route('/admin', methods=['POST'])
def admin():
    if request.form.get('token') != admin_token:
        message, success = "Wrong token.", False
    else:
        action = request.form.get('action').lower()
        if action in ('add', 'get_key'):
            nickname = request.form.get('nickname')
            if not nickname:
                message, success = "No nickname specified.", False
            else:
                if action == 'add':
                    with get_db() as db:
                        db.execute('insert into user(key, nickname) values (?, ?)', (str(uuid.uuid4()), nickname))
                    message, success = "Added %s." % nickname, True
                elif action == 'get_key':
                    user = get_db().execute('select key from user where nickname = ?', (nickname,)).fetchone()
                    if user:
                        key, = user
                        message, success = key, True
                    else:
                        message, success = "Wrong nickname: %s" % nickname, False
        else:
            message, success = "Wrong action.", False
    return message + '\n'

if __name__ == '__main__':
    app.run(debug=True)
