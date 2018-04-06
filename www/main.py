#!/usr/bin/env python3
import os
import uuid
import hashlib
import sqlite3
import threading
from flask import *
from flaskext.markdown import Markdown
from flask_uploads import *
import bot

# Flask
app = Flask(__name__)
app.jinja_options = { 'trim_blocks': True, 'lstrip_blocks': True }
app.secret_key = str(uuid.uuid4())

# Markdown
Markdown(app)

# Uploads
app.config['UPLOADS_DEFAULT_DEST'] = app.root_path
screenshots = UploadSet('screenshots', ('jpg', 'jpeg', 'png', 'bmp'))
configure_uploads(app, screenshots)
patch_request_class(app, 8 * 1024 * 1024)

# Database
database = os.path.join(app.root_path, 'db.sqlite')

def get_db():
    if not 'db' in g:
        g.db = sqlite3.connect(database)
        g.db.execute('create table if not exists user(key text primary key, nickname text, screenshot text, vote text)')
    return g.db

@app.teardown_appcontext
def close_connection(e):
    if 'db' in g:
        g.db.close()

# IRC bot
ricebot = bot.Bot(database)
threading.Thread(target=ricebot.start).start()

# Routing

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/join')
def join():
    return render_template('join.html', title='join')

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        key = request.form.get('key')
        user = get_db().execute('select nickname, screenshot from user where key = ?', (key,)).fetchone()
        if not user:
            message, success = "Wrong key.", False
        else:
            nickname, old_screenshot = user
            try:
                hashed = hashlib.sha256(request.files['screenshot'].filename.encode()).hexdigest()[:8]
                screenshot = screenshots.save(request.files['screenshot'], name='%s.' % hashed)
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

@app.errorhandler(404)
def not_found(error):
    return render_template('not_found.html', title='404'), 404

if __name__ == '__main__':
    app.run(debug=True)
