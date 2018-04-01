#!/usr/bin/env python3
from flask import Flask, render_template, request
from flask.ext.markdown import Markdown
from flask.ext.uploads import UploadSet, configure_uploads, IMAGES
from werkzeug.utils import secure_filename
import redis

app = Flask(__name__)
Markdown(app)
r = redis.Redis()
screenshots = UploadSet('photos', IMAGES)
app.config['UPLOADED_PHOTOS_DEST'] = 'static/gallery'
configure_uploads(app, screenshots)

@app.route('/')
def index():
    return render_template('index.html')

# write html input form according to this
@app.route('/submit', methods=['GET', 'POST'])
def submit():
    key = request.form['key']
    if request.method == 'POST' and 'screenshot' in request.files:
        filename = screenshots.save(request.files['screenshot'])
        r.set(key, filename)
        return filename
    return render_template('submit.html', title='submit')

@app.route('/vote')
def vote():
    return render_template('vote.html', title='vote')

@app.route('/about')
def about():
    return render_template('about.html', title='about')

if __name__ == '__main__':
    app.run(debug=True)
