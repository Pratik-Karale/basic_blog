from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterationForm,LoginForm, CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

login_manager=LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES
class User(db.Model,UserMixin):
    __tablename__="Users"
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(250),nullable=False)
    password_hash=db.Column(db.String(250),nullable=False)
    email=db.Column(db.String(250),nullable=False)
    profile_pic=db.Column(db.String(250))

    comments=relationship("Comment",backref="user")
    posts=relationship("BlogPost",back_populates="author")

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id=db.Column(db.Integer,db.ForeignKey("Users.id"))

    author=relationship("User",back_populates="posts")
    comments=relationship("Comment",backref="blog")

class Comment(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    comment=db.Column(db.String(),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey("Users.id"))
    blog_id=db.Column(db.Integer,db.ForeignKey("blog_posts.id"))

db.create_all()


@app.route('/',methods=["GET","POST"])
def get_all_posts():
    posts = BlogPost.query.all()
    is_admin=False
    if not current_user.is_anonymous:
        is_admin=current_user.id==1
    return render_template("index.html", all_posts=posts,user_logged_in=not current_user.is_anonymous,
        is_admin=is_admin
        )


@app.route('/register',methods=["POST","GET"])
def register():
    form=RegisterationForm()
    if form.validate_on_submit():
        if not User.query.filter_by(email=form.email.data).first():
            new_user=User(
                name=form.name.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data),
                profile_pic=f"https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y"
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect("/")
        else:
            flash("User Account Already Exists!")

    return render_template("register.html",form=form,user_logged_in=not current_user.is_anonymous)


@app.route('/login',methods=["GET","POST"])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        expected_user=User.query.filter_by(email=form.email.data).first()
        if (expected_user and
            check_password_hash(expected_user.password_hash,form.password.data) and
            expected_user.email==form.email.data):
            login_user(expected_user)
            return redirect("/")
        else:
            flash("Invalid Credentials!")
    return render_template("login.html",user_logged_in=not current_user.is_anonymous,form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged Out.")
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=["GET","POST"])
def show_post(post_id):
    comment_form=CommentForm()
    if comment_form.validate_on_submit():
        if current_user.is_anonymous:
            flash("You have to login to comment!")
            return redirect(url_for("login"))
        new_comment_row=Comment(
            comment=comment_form.comment.data,
            user_id=current_user.id,
            blog_id=post_id,
        )
        db.session.add(new_comment_row)
        db.session.commit()
    blog_comments=Comment.query.filter_by(blog_id=post_id)
    requested_post = BlogPost.query.get(post_id)
    is_admin=False
    if not current_user.is_anonymous:
        is_admin= ( current_user.id==1 )
    return render_template("post.html",is_admin=is_admin, post=requested_post,user_logged_in=not current_user.is_anonymous,comment_form=comment_form,comments=blog_comments)


@app.route("/about")
def about():
    return render_template("about.html",user_logged_in=not current_user.is_anonymous)


@app.route("/contact")
def contact():
    return render_template("contact.html",user_logged_in=not current_user.is_anonymous)

from functools import wraps
def admin_only(func):
    @wraps(func)
    def inner(*args,**kwargs):
        if current_user.id == 1:
            return func(*args,**kwargs)
        flash(f"You Arent Authorised to {(func.__name__+'').replace('_',' ')}")
        return redirect("/")
    return inner

@app.route("/new-post",methods=["GET","POST"])
@admin_only
@login_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        if not BlogPost.query.filter_by(title=form.title.data).first():
            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url=form.img_url.data,
                author=current_user,
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
        else:
            flash("Blog already exists!")
    return render_template("make-post.html", form=form,user_logged_in=not current_user.is_anonymous)


@app.route("/edit-post/<int:post_id>",methods=["GET","POST"])
@admin_only
@login_required
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form=CreatePostForm()
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    is_admin=False
    if not current_user.is_anonymous:
        is_admin=current_user.id==1
    return render_template(
        "make-post.html", form=edit_form,
        user_logged_in=not current_user.is_anonymous,
        is_admin=current_user.id==1
        )


@app.route("/delete/<int:post_id>")
@login_required
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
