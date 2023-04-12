from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
from flask import abort
from selenium import webdriver

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

number = 1

##LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(id=user_id).first()


gravatar = Gravatar(app, size=100, rating='g', default='retro',
                    force_default=False, force_lower=False,
                    use_ssl=False,base_url=None)


##CREATE USER TABLE IN DB
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    #This will act like a List of BlogPost objects attached to each User.
    #The "author" refers to the author property in the BlogPost class.
    tasks = relationship("Task", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")
    subtasks = relationship("Subtask", back_populates="author")
    subtasks_comments = relationship("Subtask_Comment", back_populates="sub_comment_author")


##CREATE TASK BASIC TABLE IN DB
class ToDo(UserMixin, db.Model):
    __tablename__ = "todo-basic"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(300))
    checkbox = db.Column(db.String(100))


##CREATE TASK ADVANCED TABLE IN DB
class Task(UserMixin, db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="tasks")

    text = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(250), nullable=False)
    priority = db.Column(db.String(250), nullable=False)
    deadline = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    comments = relationship("Comment", back_populates="parent_task")
    subtasks = relationship("Subtask", back_populates="parent_task")


##CREATE TASK ADVANCED TABLE IN DB
class Subtask(UserMixin, db.Model):
    __tablename__ = "subtasks"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="subtasks")

    text = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(250), nullable=False)
    priority = db.Column(db.String(250), nullable=False)
    deadline = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    subtasks_comments = relationship("Subtask_Comment", back_populates="parent_subtask")

    # ***************Child Relationship*************#
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"))
    parent_task = relationship("Task", back_populates="subtasks")


##CREATE TASK COMMENT TABLE IN DB
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    #***************Child Relationship*************#
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"))
    parent_task = relationship("Task", back_populates="comments")
    text = db.Column(db.Text, nullable=False)

##CREATE SUBTASK COMMENT TABLE IN DB
class Subtask_Comment(db.Model):
    __tablename__ = "subtasks_comments"
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    sub_comment_author = relationship("User", back_populates="subtasks_comments")

    #***************Child Relationship*************#
    subtask_id = db.Column(db.Integer, db.ForeignKey("subtasks.id"))
    parent_subtask = relationship("Subtask", back_populates="subtasks_comments")
    text = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()


######------------ BASIC VERSION WITHOUT LOGGING IN ------------- #####

@app.route('/', methods=["GET", "POST"])
def get_all_todos():
    all_todos = ToDo.query.all()
    return render_template("index.html", all_todos=all_todos)

@app.route('/home', methods=["GET", "POST"])
def home():
    return render_template("home.html")


@app.route('/add', methods=["GET", "POST"])
def add_todos():
    if request.method == 'POST':
        new_todos = ToDo(
            text=request.form.get("text"),
            checkbox="fa-square",
        )
        db.session.add(new_todos)
        db.session.commit()
    return redirect(url_for('get_all_todos'))


@app.route("/delete/<int:todo_id>")
def delete_todos(todo_id):
    todo_to_delete = ToDo.query.get(todo_id)
    db.session.delete(todo_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_todos'))



@app.route('/checkbox/<int:todo_id>', methods=["GET", "POST"])
def set_checkbox(todo_id):
    todo_to_update = ToDo.query.get(todo_id)
    if todo_to_update.checkbox == "fa-square-check":
        todo_to_update.checkbox = "fa-square"
        db.session.commit()
    elif todo_to_update.checkbox == "fa-square":
        todo_to_update.checkbox = "fa-square-check"
        db.session.commit()
    return redirect(url_for('get_all_todos'))


####### -----------LOGIN REGISTRATION AND LOGOUT -------------######

@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        check_email = User.query.filter_by(email=email).first()
        if check_email:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for("login"))
        else:
            password = form.password.data
            user = User(
                email=email,
                name=form.name.data,
                password=generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            )

            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("get_all_todos"))
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    # error = None
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("That user email does not exist. Try again or register.")
            return redirect(url_for("login"))

        else:
            password = form.password.data
            pwhash = user.password
            if check_password_hash(pwhash, password):
                login_user(user)
                return redirect(url_for("get_all_todos"))
            else:
                flash("That password is incorrect.")
                return redirect(url_for("login"))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


###### -------------- ADVANCED VERSION WITH LOGGING IN ------------- #####

@app.route('/advanced', methods=["GET", "POST"])
def all_lists():
    all_todos = ToDo.query.all()
    all_tasks = Task.query.all()
    all_subtasks = Subtask.query.all()
    return render_template("advanced.html", all_tasks=all_tasks, all_todos=all_todos, all_subtasks=all_subtasks)

###CHECKLISTS

@app.route('/save-new-checklist', methods=["GET", "POST"])
def create_new_checklist():
    global number
    all_todos = ToDo.query.all()
    title = f"New Checklist{number}"
    new_task = Task(
        text=title,
        status="New",
        priority="Set Priority",
        deadline="Set Deadline",
        author=current_user,
        date=date.today().strftime("%B %d, %Y")
    )
    db.session.add(new_task)
    db.session.commit()
    number += 1

    for todo in all_todos:
        new_subtask = Subtask(
            text=todo.text,
            status=todo.checkbox,
            priority="SetPriority",
            deadline="SetDeadline",
            author=current_user,
            parent_task=Task.query.filter_by(text=title).first()
        )
        db.session.add(new_subtask)
        db.session.commit()
        db.session.delete(todo)
        db.session.commit()
    all_tasks = Task.query.all()
    all_subtasks = Subtask.query.all()
    return render_template("advanced.html", all_tasks=all_tasks, all_subtasks=all_subtasks)

@app.route("/checklist/<int:task_id>/edit", methods=["GET", "POST"])
def edit_checklist(task_id):
    requested_task = Task.query.get(task_id)
    for subtask in requested_task.subtasks:
        new_todos = ToDo(
            text=subtask.text,
            checkbox=subtask.status,
        )
        db.session.add(new_todos)
        db.session.commit()
        db.session.delete(subtask)
        db.session.commit()
    return redirect(url_for('show_checklist', task_id=task_id))

@app.route("/checklist/<int:task_id>", methods=["GET", "POST"])
def show_checklist(task_id):
    requested_task = Task.query.get(task_id)
    all_todos = ToDo.query.all()
    return render_template("show-checklist.html", all_todos=all_todos, task=requested_task)

@app.route('/save-checklist/<int:task_id>', methods=["GET", "POST"])
def create_checklist(task_id):
    all_todos = ToDo.query.all()
    for todo in all_todos:
        new_subtask = Subtask(
            text=todo.text,
            status=todo.checkbox,
            priority="SetPriority",
            deadline="SetDeadline",
            author=current_user,
            parent_task=Task.query.get(task_id)
        )
        db.session.add(new_subtask)
        db.session.commit()
        db.session.delete(todo)
        db.session.commit()
    all_tasks = Task.query.all()
    all_subtasks = Subtask.query.all()
    return render_template("advanced.html", all_tasks=all_tasks, all_subtasks=all_subtasks)


@app.route("/edit-checklist/<int:task_id>/title", methods=["GET", "POST"])
def edit_checklist_title(task_id):
    requested_task = Task.query.get(task_id)
    all_todos = ToDo.query.all()
    if request.method == 'POST':
        title = request.form.get("text")
        requested_task.text = title
        db.session.commit()
        return redirect(url_for('show_checklist', task_id=task_id))
    return render_template("edit-checklist-title.html", task=requested_task, all_todos=all_todos)


@app.route("/checklist/<int:task_id>/delete", methods=["GET", "POST"])
def delete_checklist(task_id):
    requested_task = Task.query.get(task_id)
    all_todo = ToDo.query.all()
    for todo in all_todo:
        db.session.delete(todo)
        db.session.commit()
    db.session.delete(requested_task)
    db.session.commit()
    return redirect(url_for("all_lists"))

### TASKS

@app.route('/new_tasks', methods=["GET", "POST"])
def create_new_task():
    if request.method == 'POST':
        title = request.form.get("text")
        new_task = Task(
            text=title,
            status="New",
            priority="Set Priority",
            deadline="Set Deadline",
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_task)
        db.session.commit()
        task = Task.query.filter_by(text=title).first()
        return redirect(url_for("show_task", task_id=task.id))
    return render_template("create_task.html")

@app.route('/task/<int:task_id>', methods=["GET", "POST"])
def show_task(task_id):
    requested_task = Task.query.get(task_id)
    all_subtasks = db.session.query(Subtask).all()
    all_comments = db.session.query(Comment).all()
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to log in or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=form.text.data,
            comment_author=current_user,
            parent_task=requested_task
        )
        db.session.add(new_comment)
        db.session.commit()

    return render_template("task.html", task=requested_task, current_user=current_user, form=form,
                           all_comments=all_comments, all_subtasks=all_subtasks)

@app.route('/add-subtask/<int:task_id>', methods=["GET", "POST"])
def add_subtask(task_id):
    if request.method == 'POST':
        new_subtask = Subtask(
            text=request.form.get("text"),
            status="New",
            priority="SetPriority",
            deadline="SetDeadline",
            author=current_user,
            parent_task=Task.query.get(task_id)
        )
        db.session.add(new_subtask)
        db.session.commit()
    return redirect(url_for('show_task', task_id=task_id))

@app.route("/edit-task/<int:task_id>/title", methods=["GET", "POST"])
def edit_task_title(task_id):
    requested_task = Task.query.get(task_id)
    if request.method == 'POST':
        title = request.form.get("text")
        requested_task.text = title
        db.session.commit()
        return redirect(url_for('show_task', task_id=task_id))
    return render_template("edit-task-title.html", task=requested_task)


@app.route("/task/<int:task_id>/delete", methods=["GET", "POST"])
def delete_task(task_id):
    requested_task = Task.query.get(task_id)
    for subtask in requested_task.subtasks:
        db.session.delete(subtask)
        db.session.commit()
    for comment in requested_task.comments:
        db.session.delete(comment)
        db.session.commit()
    db.session.delete(requested_task)
    db.session.commit()
    return redirect(url_for("all_lists"))

### SUBTASKS

@app.route("/task/<int:task_id>/<int:subtask_id>/delete", methods=["GET", "POST"])
def delete_subtask(subtask_id, task_id):
    subtask_to_delete = Subtask.query.get(subtask_id)
    for comment in subtask_to_delete.subtasks_comments:
        db.session.delete(comment)
        db.session.commit()
    db.session.delete(subtask_to_delete)
    db.session.commit()
    return redirect(url_for('show_task', task_id=task_id))


if __name__ == "__main__":
    app.run(debug=True)
