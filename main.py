from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, flash, abort
from flask_bootstrap import Bootstrap
import random
from secrets import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.get("SECRET_KEY")
Bootstrap(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///JWSTimages.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Images(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    observation_id = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    suffix = db.Column(db.String(250), nullable=False)

# db.create_all()


# pics = Images.query.all()
#
#
# images = pics[:100]
imgs_per_page = 25


@app.route('/')
def home():
    all_images = Images.query.all()
    return render_template("index.html", images=all_images, pg_len=imgs_per_page)


@app.route('/gallery/forward/<int:img_id>')
def next_gallery(img_id):
    all_images = Images.query.all()
    print(f"forward: {img_id}")
    return render_template("gallery.html", images=all_images[img_id:], pg_len=imgs_per_page)


# # Gets the last upload image.id, subtracts the last uploaded + images per page to go 'back'
@app.route('/gallery/back/<int:img_id>')
def prev_gallery(img_id):
    all_images = Images.query.all()
    img_id -= (imgs_per_page*2+1) #25 images per page... - 25-25+1
    print(f"back: {img_id}")
    return render_template("gallery.html", images=all_images[img_id:], pg_len=imgs_per_page)


@app.route('/add_to_gallery')
def add_to_gallery():
    return render_template("add_to_gallery.html")


if __name__ == "__main__":
    app.run(debug=True)
