import os

from django.forms import models
from flask import Flask, render_template, request, redirect, flash, abort, url_for, session, current_app
from dotenv import load_dotenv
from wtforms import StringField, SubmitField, PasswordField, validators
from flask_wtf import FlaskForm
from sqlalchemy import ForeignKey
from flask_login import LoginManager, login_user, UserMixin, current_user, logout_user, login_required
from flask_session import Session
from sqlalchemy.orm import relationship
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from werkzeug.routing import Map, Rule, NotFound, RequestRedirect
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import URL, InputRequired, Email
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import path
from django.shortcuts import render
from flask_pager import Pager



def configure():
    load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("secret_key")
Bootstrap(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///JWSTimages.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PAGE_SIZE"] = 24
app.config["VISIBLE_PAGE_COUNT"] = 20
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
LOGIN_URL = '/login'


class Images(db.Model):
    __tablename__ = "images"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    observation_id = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    suffix = db.Column(db.String(250), nullable=False)
    child = relationship("GalleryImage", back_populates="parent")


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(250), nullable=False)


class GalleryImage(db.Model):
    __tablename__ = "gallery-image"
    id = db.Column(db.Integer, primary_key=True)
    img_id = db.Column(db.Integer, ForeignKey("images.id"))
    user_id = db.Column(db.Integer, ForeignKey("users.id"))
    parent = relationship("Images", back_populates="child")


# db.create_all()
# User.__table__.create(db.session.bind)

imgs_per_page = 24

configure()


# FORMS #
class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[InputRequired()])
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    submit = SubmitField("Create my gallery")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    submit = SubmitField("Log in")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# def index(request):
#     img_list = Images.objects.all()
#     paginator = Paginator(img_list, imgs_per_page)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
#
#     return render(request=request, template_name='main/index.html', context={'images': page_obj})


# @app.route('/', methods=['GET', 'POST'], defaults={"page": 1})
# @app.route('/<int:page>', methods=['GET'])
@app.route('/')
def home():
    og_page = request.args.get("page", 1)
    page = int(og_page or 0)
    img_list = db.session.query(Images)
    paginator = Paginator(img_list, imgs_per_page)
    print(f"paginator.page_range: {paginator.page_range}")
    count = len(paginator.page_range)
    pager = Pager(page, 177)
    pages = pager.get_pages()
    print(f"count: {count}")
    print(f"pager: {pager}")
    print(f"pages: {pages}")

    skip = (page - 1) * current_app.config["PAGE_SIZE"]
    limit = current_app.config["PAGE_SIZE"]
    all_images = img_list[skip:skip + limit]
    # try:
    #     all_images = paginator.page(page)
    #     all_images = img_list[skip: skip + limit]
    # except PageNotAnInteger:
    #     all_images = paginator.page(1)
    # except EmptyPage:
    #     all_images = paginator.page(paginator.num_pages)
    return render_template("index.html", pages=pages, images=all_images)


@app.route('/gallery/forward/<int:img_id>')
def next_gallery(img_id):
    all_images = Images.query.all()
    session['url'] = url_for('next_gallery', img_id=img_id)
    return render_template("gallery.html", images=all_images[img_id:], pg_len=imgs_per_page)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        password = form.password.data
        if User.query.filter_by(email=form.email.data).first():
            flash("This email is already registered. Log in instead.")
            return redirect(url_for("login"))
        hashed_salted_pass = generate_password_hash(password=password,
                                                    method="pbkdf2:sha256",
                                                    salt_length=8)
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_salted_pass
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == "POST":
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            password = form.password.data
            if not user:
                flash("That email does not exist. Please try again.")
            elif not check_password_hash(pwhash=user.password, password=password):
                flash("The password is incorrect. Please try again or register an account.")
                return redirect(url_for("login"))
            else:
                login_user(user)
                # If the user registers,
                # the below code should return the user to the page they were at,
                # before registering...
                try:
                    return redirect(url_for(session['url']))
                except KeyError:
                    return redirect(url_for("home"))
    return render_template("login.html", form=form)


@app.route('/logout')
def log_out():
    logout_user()
    return redirect(url_for("home"))


# # Gets the last upload image.id, subtracts the last uploaded + images per page to go 'back'
@app.route('/gallery/back/<int:img_id>')
def prev_gallery(img_id):
    all_images = Images.query.all()
    img_id -= (imgs_per_page*2)  # 25 images per page... - 25-25
    return render_template("gallery.html", images=all_images[img_id:], pg_len=imgs_per_page)


@app.route('/add/<int:user_id>/<int:img_id>', methods=["GET", "POST"])
@login_required
def add(user_id, img_id):
    user = user_id
    img = img_id
    check_for_img = GalleryImage.query.filter_by(img_id=img, user_id=user).scalar()
    if check_for_img:
        pass
    else:
        new_img = GalleryImage(
            user_id=user,
            img_id=img
        )
        db.session.add(new_img)
        db.session.commit()
    return redirect(session['url'])


@app.route('/delete/<int:user_id>/<int:img_id>', methods=["GET", "POST"])
@login_required
def delete(user_id, img_id):
    user = user_id
    img = img_id
    GalleryImage.query.filter_by(img_id=img).delete()
    db.session.commit()
    return redirect(url_for("my_gallery", user_id=user))


@app.route('/my_gallery/<int:user_id>', methods=["GET", "POST"])
@login_required
def my_gallery(user_id):
    query = GalleryImage.query.filter(GalleryImage.user_id==user_id).all()
    return render_template("my_gallery.html", query=query, pg_len=len(query)-1)


if __name__ == "__main__":
    app.run(debug=True)
