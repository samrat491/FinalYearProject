from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secretkey123"
DB_NAME = "database.db"

def get_db():
    return sqlite3.connect(DB_NAME)

def init_db():
    db = get_db()
    cursor = db.cursor()
    # 1. User Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            gender TEXT,
            birthdate TEXT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    # 2. Stories Table (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_name TEXT,
            title TEXT NOT NULL,
            genre TEXT,
            tags TEXT,
            synopsis TEXT
        )
    """)
    # 3. Chapters Table (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chapters(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER,
            chapter_number INTEGER,
            chapter_title TEXT,
            content TEXT,
            FOREIGN KEY(story_id) REFERENCES stories(id)
        )
    """)
    db.commit()
    db.close()

init_db()

@app.route("/home")
def home():
    user = session.get("user")
    db = get_db()
    cursor = db.cursor()
    # Fetch the 4 newest stories to show on the homepage
    cursor.execute("SELECT id, title, genre FROM stories ORDER BY id DESC LIMIT 4")
    latest_stories = [{"id": row[0], "title": row[1], "genre": row[2]} for row in cursor.fetchall()]
    db.close()
    return render_template("home.html", user=user, latest_stories=latest_stories)

@app.route("/", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect("/dashboard")
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT name, password FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        db.close()
        if user and check_password_hash(user[1], password):
            session["user"] = user[0]
            return redirect("/dashboard")
        else:
            flash("Invalid email or password")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        gender = request.form["gender"]
        birthdate = request.form["birthdate"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                """INSERT INTO users (name, gender, birthdate, email, password) VALUES (?,?,?,?,?)""",
                (name, gender, birthdate, email, password)
            )
            db.commit()
            db.close()
            flash("Account created successfully")
            return redirect("/")
        except:
            flash("Email already exists")
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html", user=session["user"])

@app.route("/create-story")
def create_story():
    if "user" not in session:
        return redirect("/")
    return render_template("createstory.html")

# UPDATED: Accept POST data from the create story form
@app.route("/chapter", methods=["GET", "POST"])
def chapter():
    if "user" not in session:
        return redirect("/")
    
    if request.method == "POST":
        # Temporarily hold the story info so we can pass it to the chapter editor
        story_data = {
            "title": request.form.get("title"),
            "genre": request.form.get("genre"),
            "tags": request.form.get("tags"),
            "synopsis": request.form.get("synopsis")
        }
        return render_template("chapter.html", story_data=story_data)
    
    return redirect("/create-story")

# NEW: Save the final story AND chapter into the database
@app.route("/publish", methods=["POST"])
def publish():
    if "user" not in session:
        return redirect("/")

    author = session["user"]
    title = request.form.get("title")
    genre = request.form.get("genre")
    tags = request.form.get("tags")
    synopsis = request.form.get("synopsis")
    
    chap_number = request.form.get("chapter_number")
    chap_title = request.form.get("chapter_title")
    content = request.form.get("content")

    db = get_db()
    cursor = db.cursor()
    # 1. Insert Story
    cursor.execute(
        "INSERT INTO stories (author_name, title, genre, tags, synopsis) VALUES (?, ?, ?, ?, ?)",
        (author, title, genre, tags, synopsis)
    )
    story_id = cursor.lastrowid # Get the ID of the story we just made
    
    # 2. Insert Chapter tied to that Story
    cursor.execute(
        "INSERT INTO chapters (story_id, chapter_number, chapter_title, content) VALUES (?, ?, ?, ?)",
        (story_id, chap_number, chap_title, content)
    )
    db.commit()
    db.close()
    
    return redirect("/home") # Send user back to home to see their book!




# ADD THIS NEW ROUTE TO APP.PY
@app.route("/read/<int:story_id>")
def read_story(story_id):
    db = get_db()
    cursor = db.cursor()
    
    # Get the story info (Title, Author, Synopsis)
    cursor.execute("SELECT title, author_name, synopsis FROM stories WHERE id=?", (story_id,))
    story = cursor.fetchone()
    
    # Get all chapters for this story
    cursor.execute("SELECT chapter_number, chapter_title, content FROM chapters WHERE story_id=? ORDER BY chapter_number ASC", (story_id,))
    chapters = cursor.fetchall()
    db.close()
    
    # If someone types a random URL for a story that doesn't exist, send them home
    if not story:
        return redirect("/home")
        
    return render_template("read.html", story=story, chapters=chapters)




@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")




if __name__ == "__main__":
    app.run(debug=True)




    