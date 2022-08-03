import os
from flask import Flask, render_template, request, redirect, flash, abort, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, SubmitField, PasswordField, validators
from wtforms.validators import URL, InputRequired, Email
from flask_login import LoginManager, login_user, UserMixin, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_bootstrap import Bootstrap
from sqlalchemy import ForeignKey
from flask_wtf import FlaskForm
from dotenv import load_dotenv


def configure():
    load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("secret_key")
Bootstrap(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///JWSTimages.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


class Images(db.Model):
    __tablename__ = "images"
    id = db.Column(db.Integer, primary_key=True, unique=True)
    observation_id = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    suffix = db.Column(db.String(250), nullable=False)


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


# db.create_all()
# User.__table__.create(db.session.bind)


imgs_per_page = 25

configure()


# FORMS #
class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[InputRequired()])
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    confirm_pass = PasswordField("Confirm Password", validators=[InputRequired()])
    submit = SubmitField("Create my gallery")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    submit = SubmitField("Log in")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def home():
    all_images = Images.query.all()
    return render_template("index.html", images=all_images, pg_len=imgs_per_page)


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
                flash("The password is incorrect. Please try again or register an account")
                return redirect(url_for("login"))
            else:
                login_user(user)
                return redirect(url_for("home"))
    return render_template("login.html", form=form)


@app.route('/logout')
def log_out():
    logout_user()
    return redirect(url_for("home"))


@app.route('/gallery/forward/<int:img_id>')
def next_gallery(img_id):
    all_images = Images.query.all()
    return render_template("gallery.html", images=all_images[img_id:], pg_len=imgs_per_page)


# # Gets the last upload image.id, subtracts the last uploaded + images per page to go 'back'
@app.route('/gallery/back/<int:img_id>')
def prev_gallery(img_id):
    all_images = Images.query.all()
    img_id -= (imgs_per_page*2+1) #25 images per page... - 25-25+1
    print(f"back: {img_id}")
    return render_template("gallery.html", images=all_images[img_id:], pg_len=imgs_per_page)


@app.route('/add/<int:user_id>/<int:img_id>', methods=["GET", "POST"])
@login_required
def add(user_id, img_id):
    user_id = user_id
    img_id = img_id

    new_img = GalleryImage(
        user_id=user_id,
        img_id=img_id
    )
    db.session.add(new_img)
    db.session.commit()
    all_images = Images.query.all()
    return render_template("gallery.html", images=all_images[img_id:], pg_len=imgs_per_page)


@app.route('/my_gallery/<int:user_id>', methods=["GET", "POST"])
@login_required
def my_gallery(user_id):
    query = db.session.query(GalleryImage).filter_by(user_id=user_id).all()
    all_images = db.session.query(Images).filter_by(id=query).all()
    print(all_images)

    # print(all_images)
    # all_images = Images.query.filter_by(email=form.email.data).first()
    # print(all_images)

    return render_template("my_gallery.html", images=all_images, pg_len=len(all_images))


if __name__ == "__main__":
    app.run(debug=True)
