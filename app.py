import os
import sys

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

from models import db
from scrapeNProcess import fetch_and_process_articles

# pull in the GOOGLE_SQL password if not already in environ (for local use only)
if os.environ.get('GOOGLE_SQL') is None:
    # pull in gcloud SQL key securely
    with open('pass/GOOGLE_SQL', 'r') as f:
        os.environ['GOOGLE_SQL'] = f.read()
        print('GOOGLE_SQL is imported from local store')

# pull in the DB_PUBLIC_IP password if not already in environ (for local use only)
if os.environ.get('DB_PUBLIC_IP') is None:
    # pull in db public ip securely
    with open('pass/DB_PUBLIC_IP', 'r') as f:
        os.environ['DB_PUBLIC_IP'] = f.read()
        print('DB_PUBLIC_IP is imported from local store')

# pull in the DB_CONN_NAME password if not already in environ (for local use only)
if os.environ.get('DB_CONN_NAME') is None:
    # pull in db public ip securely
    with open('pass/DB_CONN_NAME', 'r') as f:
        os.environ['DB_CONN_NAME'] = f.read()
        print('DB_CONN_NAME is imported from local store')

app = Flask(__name__)

#set environment variables
#app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

db_uri = f'mysql+pymysql://root:{os.environ.get('GOOGLE_SQL')}@localhost/newsgpt-articles?unix_socket=/cloudsql/{os.environ.get('DB_CONN_NAME')}' 

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy with Flask app
db.init_app(app)

with app.app_context():
    db.create_all()  # Create tables

@app.route('/')
def home():
    try:
        articles = fetch_and_process_articles(db)
    except Exception as e:
        print(f'fetch and process failed in app generation\n\n {e}')
        articles = [
            {'title':'oops', 
             'url': 'www.google.com', 
             'headline' : 'needs work'}
             ]
        e_type, e_object, e_traceback = sys.exc_info()
        e_filename = os.path.split(e_traceback.tb_frame.f_code.co_filename)[1]
        e_message = str(e)
        e_line_number = e_traceback.tb_lineno

        print(f'exception type: {e_type}')
        print(f'exception filename: {e_filename}')
        print(f'exception line number: {e_line_number}')
        print(f'exception message: {e_message}')
    return render_template('home.html', articles=articles)

@app.route('/up')
def up():
    return "<p>GORT is up!</p>"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT',8080)))