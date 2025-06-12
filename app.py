from flask import Flask, render_template, url_for, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

app = Flask(__name__)

#db: setting and initializing
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///db.sqlite'
app.config["SQLITE_TRACK_MODIFICATIONS"]= False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

#______class / models_____
#text model
class Text(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    creation_date = db.Column(db.DateTime, default=datetime.now())
    
    def __repr__(self):
        return f"<Text: {self.id}, title: {self.title}>"

#tag model
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag_name = db.Column(db.String(28), nullable=True, unique=True, default="uncatogorized")
    
    def __repr__(self):
        return f"<Tag: {self.id} named {self.tag_name}>"

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


