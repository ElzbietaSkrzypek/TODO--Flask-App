from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from forms import RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

##LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(id=user_id).first()


gravatar = Gravatar(app, size=100, rating='g', default='retro',
                    force_default=False, force_lower=False,
                    use_ssl=False, base_url=None)

##CREATE SECONDARY TABLES IN DB FOR MANY TO MANY RELATIONSHIP
user_checklist = db.Table('user_checklist',
                          db.Column('users_id', db.Integer, db.ForeignKey('users.id')),
                          db.Column('checklist_id', db.Integer, db.ForeignKey('checklist.id'))
                          )

user_task = db.Table('user_task',
                     db.Column('users_id', db.Integer, db.ForeignKey('users.id')),
                     db.Column('tasks_id', db.Integer, db.ForeignKey('tasks.id'))
                     )


##CREATE USER TABLE IN DB
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # ***************Parent Relationship*************#
    tasks = relationship("Task", secondary=user_task, backref="author")
    checklist = relationship("Checklist", secondary=user_checklist, backref="author")

    comments = relationship("Comment", back_populates="comment_author")
    subtasks_comments = relationship("Subtask_Comment", back_populates="sub_comment_author")


##CREATE TASK BASIC TABLE IN DB
class ToDoBasic(UserMixin, db.Model):
    __tablename__ = "todo_basic"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(300))
    checkbox = db.Column(db.String(100))


##CREATE TASK ADVANCED TABLE IN DB
class Checklist(UserMixin, db.Model):
    __tablename__ = "checklist"
    id = db.Column(db.Integer, primary_key=True)

    text = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    todo = relationship("ToDo", back_populates="parent_checklist")



##CREATE TASK ADVANCED TABLE IN DB
class ToDo(UserMixin, db.Model):
    __tablename__ = "todo"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(300))
    checkbox = db.Column(db.String(100))

    # ***************Child Relationship*************#
    checklist_id = db.Column(db.Integer, db.ForeignKey("checklist.id"))
    parent_checklist = relationship("Checklist", back_populates="todo")


##CREATE TASK ADVANCED TABLE IN DB
class Task(UserMixin, db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)


    text = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(250), nullable=False)
    priority = db.Column(db.String(250), nullable=False)
    deadline = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    comments = relationship("Comment", back_populates="parent_task")
    subtasks = relationship("Subtask", back_populates="parent_task")


##CREATE SUBTASK ADVANCED TABLE IN DB
class Subtask(UserMixin, db.Model):
    __tablename__ = "subtasks"
    id = db.Column(db.Integer, primary_key=True)

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

    # ***************Child Relationship*************#
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"))
    parent_task = relationship("Task", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


##CREATE SUBTASK COMMENT TABLE IN DB
class Subtask_Comment(db.Model):
    __tablename__ = "subtasks_comments"
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    sub_comment_author = relationship("User", back_populates="subtasks_comments")

    # ***************Child Relationship*************#
    subtask_id = db.Column(db.Integer, db.ForeignKey("subtasks.id"))
    parent_subtask = relationship("Subtask", back_populates="subtasks_comments")
    text = db.Column(db.Text, nullable=False)


with app.app_context():
    db.create_all()


######------------ BASIC VERSION WITHOUT LOGGING IN ------------- #####

@app.route('/', methods=["GET", "POST"])
def get_all_todos():
    all_todos = ToDoBasic.query.all()
    return render_template("index.html", all_todos=all_todos)


@app.route('/home', methods=["GET", "POST"])
def home():
    return render_template("home.html")


@app.route('/add', methods=["GET", "POST"])
def add_todos():
    if request.method == 'POST':
        new_todos = ToDoBasic(
            text=request.form.get("text"),
            checkbox="fa-square",
        )
        db.session.add(new_todos)
        db.session.commit()
    return redirect(url_for('get_all_todos'))


@app.route("/delete/<int:todo_id>")
def delete_todos(todo_id):
    todo_to_delete = ToDoBasic.query.get(todo_id)
    db.session.delete(todo_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_todos'))


@app.route('/checkbox/<int:todo_id>', methods=["GET", "POST"])
def set_checkbox(todo_id):
    todo_to_update = ToDoBasic.query.get(todo_id)
    if todo_to_update.checkbox == "fa-square-check":
        todo_to_update.checkbox = "fa-square"
        db.session.commit()
    elif todo_to_update.checkbox == "fa-square":
        todo_to_update.checkbox = "fa-square-check"
        db.session.commit()
    return redirect(url_for('get_all_todos'))


####### -----------LOGIN REGISTRATION AND LOGOUT -------------######

def logged_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("You need to log in or register to access.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


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
@logged_only
def all_lists():
    all_tasks = Task.query.all()
    all_checklist = Checklist.query.all()
    return render_template("advanced.html", all_tasks=all_tasks, all_checklist=all_checklist)


###CHECKLISTS


@app.route('/save-new-checklist', methods=["GET", "POST"])
@logged_only
def create_new_checklist():
    all_todos = ToDoBasic.query.all()
    title = f"New Checklist"
    new_checklist = Checklist(
        text=title,
    )
    db.session.add(new_checklist)
    db.session.commit()

    current_user.checklist.append(new_checklist)
    db.session.commit()

    for todo in all_todos:
        new_todos = ToDo(
            text=todo.text,
            checkbox=todo.checkbox,
            parent_checklist=new_checklist)
        db.session.add(new_todos)
        db.session.commit()
        db.session.delete(todo)
        db.session.commit()
    all_checklists = Checklist.query.all()
    all_todos = ToDo.query.all()
    all_tasks = Task.query.all()
    all_subtasks = Subtask.query.all()
    return render_template("advanced.html", all_checklist=all_checklists, all_todos=all_todos,
                           all_tasks=all_tasks, all_subtasks=all_subtasks)


@app.route("/checklist/<int:checklist_id>/edit", methods=["GET", "POST"])
@logged_only
def edit_checklist(checklist_id):
    requested_checklist = Checklist.query.get(checklist_id)
    return render_template("show-checklist.html", checklist=requested_checklist)


@app.route("/checklist/<int:checklist_id>/add", methods=["GET", "POST"])
@logged_only
def add_todo_checklist(checklist_id):
    requested_checklist = Checklist.query.get(checklist_id)
    if request.method == 'POST':
        new_todos = ToDo(
            text=request.form.get("text"),
            checkbox="fa-square",
            parent_checklist=requested_checklist
        )
        db.session.add(new_todos)
        db.session.commit()
    return render_template("show-checklist.html", checklist=requested_checklist)


@app.route('/checklist/<int:checklist_id>/checkbox/<int:todo_id>', methods=["GET", "POST"])
@logged_only
def set_checkbox_todo(todo_id, checklist_id):
    requested_checklist = Checklist.query.get(checklist_id)
    todo_to_update = ToDo.query.get(todo_id)
    if todo_to_update.checkbox == "fa-square-check":
        todo_to_update.checkbox = "fa-square"
        db.session.commit()
    elif todo_to_update.checkbox == "fa-square":
        todo_to_update.checkbox = "fa-square-check"
        db.session.commit()
    return render_template("show-checklist.html", checklist=requested_checklist)


@app.route("/edit-checklist/<int:checklist_id>/title", methods=["GET", "POST"])
@logged_only
def edit_checklist_title(checklist_id):
    requested_checklist = Checklist.query.get(checklist_id)
    if request.method == 'POST':
        title = request.form.get("text")
        requested_checklist.text = title
        db.session.commit()
        return redirect(url_for('edit_checklist', checklist_id=checklist_id))
    return render_template("edit-checklist-title.html", checklist=requested_checklist)


@app.route("/checklist/<int:checklist_id>/todo/<int:todo_id>/delete")
@logged_only
def checklist_todos_delete(todo_id, checklist_id):
    todo_to_delete = ToDo.query.get(todo_id)
    db.session.delete(todo_to_delete)
    db.session.commit()
    return redirect(url_for('edit_checklist', checklist_id=checklist_id))


@app.route("/checklist/<int:checklist_id>/delete", methods=["GET", "POST"])
@logged_only
def delete_checklist(checklist_id):
    requested_checklist = Checklist.query.get(checklist_id)
    for todo in requested_checklist.todo:
        db.session.delete(todo)
        db.session.commit()
    db.session.delete(requested_checklist)
    db.session.commit()
    return redirect(url_for("all_lists"))

@app.route('/checklist/<int:checklist_id>/addcolab', methods=["GET", "POST"])
@logged_only
def checklist_add_collaborators(checklist_id):
    checklist = Checklist.query.get(checklist_id)
    if request.method == "POST":
        email = request.form.get("collaborator")
        user = User.query.filter_by(email=email).first()
        if not user:
            message = "There is no user with that email."
            return render_template("show-checklist.html", checklist=checklist, message=message)
        user.checklist.append(checklist)
        db.session.commit()
        return redirect(url_for('edit_checklist', checklist_id=checklist_id))
    return render_template('add-checklist-collaborator.html', checklist=checklist)


### TASKS


@app.route('/new_tasks', methods=["GET", "POST"])
@logged_only
def create_new_task():
    if request.method == 'POST':
        title = request.form.get("text")
        new_task = Task(
            text=title,
            status="New",
            priority="Set Priority",
            deadline="Set Deadline",
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_task)
        db.session.commit()
        current_user.tasks.append(new_task)
        db.session.commit()
        task = Task.query.filter_by(text=title).first()
        return redirect(url_for("show_task", task_id=task.id))
    return render_template("create_task.html")


@app.route('/task/<int:task_id>', methods=["GET", "POST"])
@logged_only
def show_task(task_id):
    requested_task = Task.query.get(task_id)
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

    return render_template("task.html", task=requested_task, current_user=current_user, form=form)


@app.route('/add-subtask/<int:task_id>', methods=["GET", "POST"])
@logged_only
def add_subtask(task_id):
    if request.method == 'POST':
        new_subtask = Subtask(
            text=request.form.get("text"),
            status="Set-Status",
            priority="Set-Priority",
            deadline="Set-Deadline",
            parent_task=Task.query.get(task_id)
        )
        db.session.add(new_subtask)
        db.session.commit()
    return redirect(url_for('show_task', task_id=task_id))


@app.route("/edit-task/<int:task_id>/title", methods=["GET", "POST"])
@logged_only
def edit_task_title(task_id):
    requested_task = Task.query.get(task_id)
    if request.method == 'POST':
        title = request.form.get("text")
        requested_task.text = title
        db.session.commit()
        return redirect(url_for('show_task', task_id=task_id))
    return render_template("edit-task-title.html", task=requested_task)


@app.route("/task/<int:task_id>/delete", methods=["GET", "POST"])
@logged_only
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

@app.route("/task/<int:task_id>/comment-delete/<int:comment_id>", methods=["GET", "POST"])
@logged_only
def delete_comment(task_id, comment_id):
    requested_comment = Comment.query.get(comment_id)
    db.session.delete(requested_comment)
    db.session.commit()
    return redirect(url_for("show_task", task_id=task_id))


@app.route('/task/<int:task_id>/addcolab', methods=["GET", "POST"])
@logged_only
def add_collaborators(task_id):
    task = Task.query.get(task_id)
    if request.method == "POST":
        email = request.form.get("collaborator")
        user = User.query.filter_by(email=email).first()
        if not user:
            message = "There is no user with that email."
            form= CommentForm()
            return render_template("task.html", task=task, current_user=current_user, form=form, message=message)
        task = Task.query.get(task_id)
        user.tasks.append(task)
        db.session.commit()
        return redirect(url_for('show_task', task_id=task_id))
    return render_template('add_task_collaborator.html', task=task)


@app.route('/task/<int:task_id>/leave_colab', methods=["GET", "POST"])
@logged_only
def leave_collaborators(task_id):
    user = current_user
    task = Task.query.get(task_id)
    user.tasks.remove(task)
    db.session.commit()
    return redirect(url_for("all_lists"))



### SUBTASKS


@app.route("/task/<int:task_id>/<int:subtask_id>/delete", methods=["GET", "POST"])
@logged_only
def delete_subtask(subtask_id, task_id):
    subtask_to_delete = Subtask.query.get(subtask_id)
    for comment in subtask_to_delete.subtasks_comments:
        db.session.delete(comment)
        db.session.commit()
    db.session.delete(subtask_to_delete)
    db.session.commit()
    return redirect(url_for('show_task', task_id=task_id))


@app.route('/subtask/<int:subtask_id>', methods=["GET", "POST"])
@logged_only
def show_subtask(subtask_id):
    requested_subtask = Subtask.query.get(subtask_id)
    all_comments = db.session.query(Subtask_Comment).all()
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to log in or register to comment.")
            return redirect(url_for("login"))

        new_comment = Subtask_Comment(
            text=form.text.data,
            sub_comment_author=current_user,
            parent_subtask=requested_subtask
        )
        db.session.add(new_comment)
        db.session.commit()

    return render_template("subtask.html", subtask=requested_subtask, current_user=current_user, form=form,
                           all_comments=all_comments)


@app.route('/subtask/<int:subtask_id>/new', methods=["GET", "POST"])
@logged_only
def set_status_new(subtask_id):
    subtask = Subtask.query.get(subtask_id)
    subtask.status = "New"
    db.session.commit()
    return redirect(url_for('show_subtask', subtask_id=subtask_id))


@app.route('/subtask/<int:subtask_id>/inprogress', methods=["GET", "POST"])
@logged_only
def set_status_inprogress(subtask_id):
    subtask = Subtask.query.get(subtask_id)
    subtask.status = "In Progress"
    db.session.commit()
    return redirect(url_for('show_subtask', subtask_id=subtask_id))


@app.route('/subtask/<int:subtask_id>/completed', methods=["GET", "POST"])
@logged_only
def set_status_completed(subtask_id):
    subtask = Subtask.query.get(subtask_id)
    subtask.status = "Completed"
    db.session.commit()
    return redirect(url_for('show_subtask', subtask_id=subtask_id))


@app.route('/subtask/<int:subtask_id>/low', methods=["GET", "POST"])
@logged_only
def set_status_low(subtask_id):
    subtask = Subtask.query.get(subtask_id)
    subtask.priority = "Low"
    db.session.commit()
    return redirect(url_for('show_subtask', subtask_id=subtask_id))


@app.route('/subtask/<int:subtask_id>/middle', methods=["GET", "POST"])
@logged_only
def set_status_middle(subtask_id):
    subtask = Subtask.query.get(subtask_id)
    subtask.priority = "Middle"
    db.session.commit()
    return redirect(url_for('show_subtask', subtask_id=subtask_id))


@app.route('/subtask/<int:subtask_id>/high', methods=["GET", "POST"])
@logged_only
def set_status_high(subtask_id):
    subtask = Subtask.query.get(subtask_id)
    subtask.priority = "High"
    db.session.commit()
    return redirect(url_for('show_subtask', subtask_id=subtask_id))


@app.route('/subtask/<int:subtask_id>/deadline', methods=["GET", "POST"])
@logged_only
def save_deadline(subtask_id):
    subtask = Subtask.query.get(subtask_id)
    if request.method == 'POST':
        subtask.deadline = request.form["deadline"]
        db.session.commit()
        print(request.form["deadline"])
    return redirect(url_for('show_subtask', subtask_id=subtask_id))


@app.route("/subtask/<int:subtask_id>/comment-delete/<int:comment_id>", methods=["GET", "POST"])
@logged_only
def delete_subtask_comment(subtask_id, comment_id):
    requested_comment = Subtask_Comment.query.get(comment_id)
    db.session.delete(requested_comment)
    db.session.commit()
    return redirect(url_for("show_subtask", subtask_id=subtask_id))





if __name__ == "__main__":
    app.run(debug=True)
