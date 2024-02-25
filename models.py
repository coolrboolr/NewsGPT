from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    headline = db.Column(db.Text, nullable=True)  # Generated headline

    def __repr__(self):
        return '<Article %r>' % self.title
    