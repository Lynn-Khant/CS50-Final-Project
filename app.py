import os

from cs50 import SQL
from flask import Flask,redirect, render_template, request, session
from flask_session import Session
from datetime import datetime,timedelta,date
from werkzeug.security import check_password_hash, generate_password_hash
from helper import login_required
# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///assignments.db")

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    current_date = date.today()
    daysLeftUpdate = db.execute("SELECT id,daysLeft,deadline FROM assignments")
    for i in daysLeftUpdate:
        date1 = datetime.strptime(current_date.strftime("%Y-%m-%d"), '%Y-%m-%d')
        date2 = datetime.strptime(i["deadline"], '%Y-%m-%d')
        difference = date2 - date1
        if difference.days<=0:
            db.execute("Update assignments SET daysLeft=? WHERE id=?",0,i["id"])
        else:
            db.execute("Update assignments SET daysLeft=? WHERE id=?",difference.days,i["id"])
    if request.args.get("weeks"):
        logged_in_user = session["user_id"]
        assignments = db.execute("SELECT * FROM assignments WHERE userId=? AND weekId=(SELECT id FROM weeks WHERE startingDate=?)",logged_in_user,request.args.get("weeks"))
        current_week = db.execute("SELECT * FROM weeks WHERE startingDate=?",request.args.get("weeks"))
        weeks = db.execute("SELECT * FROM weeks")
        return render_template("index.html",assignments=assignments,starting_date=current_week[0]["startingDate"],ending_date=current_week[0]["endingDate"],weeks=weeks)
    else:
        logged_in_user = session["user_id"]
        current_date = date.today()
        week_day = datetime.today().weekday()
        starting_date = current_date - timedelta(days=week_day)
        ending_date = current_date + timedelta(days=6-week_day)
        assignments = db.execute("SELECT * FROM assignments WHERE userId=? AND weekId=(SELECT id FROM weeks WHERE startingDate=?)",logged_in_user,starting_date)
        weeks = db.execute("SELECT * FROM weeks")
        return render_template("index.html",assignments=assignments,starting_date=starting_date,ending_date=ending_date,weeks=weeks)

@app.route("/create", methods=["GET", "POST"])
@login_required
def form():
    values = {}
    if request.method == "POST":
        errors = {}
        if not request.form.get("assignment"):
            errors["assignment"]="Assignment name is required."
        else:
            values["assignment"]=request.form.get("assignment")
        if not request.form.get("deadline"):
            errors["deadline"]="Deadline date is required."
        else:
            values["deadline"]=request.form.get("deadline")
        if not request.form.get("subject"):
            errors["subject"]="Subject name is required."
        else:
            values["subject"]=request.form.get("subject")
        if errors:
            
            return render_template("create.html",errors=errors,values=values)
        else:
            current_date = date.today()
            week_day = datetime.today().weekday()
            ending_date = current_date + timedelta(days=6-week_day)
            starting_date = current_date - timedelta(days=week_day)
            checking = db.execute("SELECT * FROM weeks WHERE startingDate=?",starting_date)
            print(checking)
            if week_day == 0 and len(checking) == 0:
                db.execute("INSERT INTO weeks (startingDate,endingDate) VALUES(?,?)",starting_date,ending_date)
                last_inserted_week = db.execute("SELECT last_insert_rowid()")
                print(last_inserted_week)
                date1 = datetime.strptime(current_date.strftime("%Y-%m-%d"), '%Y-%m-%d')
                date2 = datetime.strptime(request.form.get("deadline"), '%Y-%m-%d')
                difference = date2 - date1
                db.execute("INSERT INTO assignments(deadline,daysLeft,assignment,subject,progress,status,weekId,userId) VALUES(?,?,?,?,?,?,?,?)",request.form.get("deadline"),difference.days,request.form.get("assignment"),request.form.get("subject"),0,"unfinished",last_inserted_week[0]["last_insert_rowid()"],session["user_id"])
                return redirect("/")
            else:
                last_week_id = db.execute("SELECT id FROM weeks ORDER BY id DESC LIMIT 1")
                print(last_week_id)
                date1 = datetime.strptime(current_date.strftime("%Y-%m-%d"), '%Y-%m-%d')
                date2 = datetime.strptime(request.form.get("deadline"), '%Y-%m-%d')
                difference = date2 - date1
                db.execute("INSERT INTO assignments(deadline,daysLeft,assignment,subject,progress,status,weekId,userId) VALUES(?,?,?,?,?,?,?,?)",request.form.get("deadline"),difference.days,request.form.get("assignment"),request.form.get("subject"),0,"unfinished",last_week_id[0]["id"],session["user_id"])
                return redirect("/")
    else:
        return render_template("create.html",values=values)
    
@app.route("/register", methods=["GET", "POST"])
def register():
    values = {}
    if request.method == "POST":
        errors = {}
        if not request.form.get("name"):
            errors["name"]="User name is required."
        else:
            values["name"]=request.form.get("name")
        if not request.form.get("email"):
            errors["email"]="Email is required."
        else:
            values["email"]=request.form.get("email")
        if not request.form.get("password"):
            errors["password"]="Password is required."
        else:
            values["password"]=request.form.get("password")
        if not request.form.get("confirm"):
            errors["confirm"]="Confirm Password is required."
        else:
            values["confirm"]=request.form.get("confirm")
        if request.form.get("password") != request.form.get("confirm"):
            errors["equal"]="Passwords must be the same"
        if errors:
            return render_template("register.html",errors=errors,values=values)
        try:
            hashed_password=generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users(name,email,password,confirm) VALUES(?,?,?,?)",request.form.get("name"),request.form.get("email"),hashed_password,hashed_password)
            return redirect("/")
        except ValueError:
            errors["emailtaken"]="This email is already used."
            return render_template("register.html",errors=errors,values=values)
    else:
        return render_template("register.html",values=values)
    
@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    values = {}
    if request.method == "POST":
        errors = {}
        if not request.form.get("email"):
            errors["email"] = "Email is required."
        else:
            values["email"] = request.form.get("email")
        if not request.form.get("password"):
            errors["password"] = "Password is required."
        rows = db.execute(
            "SELECT * FROM users WHERE email = ?", request.form.get("email")
        )
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            errors["credentials"] = "Wrong login credentials."
        if errors:
            return render_template("login.html",errors=errors,values=values)
        session["user_id"] = rows[0]["id"]
        return redirect("/")
    else:
        return render_template("login.html",values=values)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/update", methods=["GET", "POST"])
def update():
    new_values = {}
    if request.method == "POST":
        old_values = db.execute("SELECT * FROM assignments WHERE id=?",request.form.get("assignmentId"))
        errors = {}
        if not request.form.get("assignment"):
            errors["assignment"]="Assignment name is required."
        else:
            new_values["assignment"]=request.form.get("assignment")
        if not request.form.get("deadline"):
            errors["deadline"]="Deadline date is required."
        else:
            new_values["deadline"]=request.form.get("deadline")
        if not request.form.get("subject"):
            errors["subject"]="Subject name is required."
        else:
            new_values["subject"]=request.form.get("subject")
        if not request.form.get("progress"):
            errors["progress"]="Updated Progress is required."
        else:
            new_values["progress"]=request.form.get("progress")
        if not request.form.get("status"):
            errors["status"]="New status is required."
        else:
            new_values["status"]=request.form.get("status")
        if errors:
            # print("this is running")
            # print(errors)
            return render_template("update.html",errors=errors,new_values=new_values,old_values=old_values[0])
        else:
            # print("this one is running instead")
            current_date = date.today()
            date1 = datetime.strptime(current_date.strftime("%Y-%m-%d"), '%Y-%m-%d')
            date2 = datetime.strptime(new_values["deadline"], '%Y-%m-%d')
            difference = date2 - date1
            db.execute("Update assignments SET deadline=?, daysLeft=?, assignment=?, subject=?, progress=?, status=? WHERE id=?",new_values["deadline"],difference.days,new_values["assignment"],new_values["subject"],new_values["progress"],new_values["status"],request.form.get("assignmentId"))
            return redirect("/")
    else:
        old_values = db.execute("SELECT * FROM assignments WHERE id=?",request.args.get("assignmentId"))
        return render_template("update.html",new_values=new_values,old_values=old_values[0])