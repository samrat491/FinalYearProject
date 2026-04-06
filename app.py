from flask import Flask, render_template, request, redirect, flash, session, url_for
import sqlite3
import os 
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename # NEW: Safely handles uploaded files

app = Flask(__name__)
app.secret_key = "secretkey123"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, "database.db")

# NEW: Create a folder to store uploaded cover images
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Makes the folder if it doesn't exist

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
    # 2. Stories Table (UPDATED: Added cover_image TEXT)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_name TEXT,
            title TEXT NOT NULL,
            genre TEXT,
            tags TEXT,
            synopsis TEXT,
            cover_image TEXT
        )
    """)
    # 3. Chapters Table
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
    # UPDATED: Fetch cover_image as well
    cursor.execute("SELECT id, title, genre, cover_image FROM stories ORDER BY id DESC LIMIT 4")
    latest_stories = [{"id": row[0], "title": row[1], "genre": row[2], "cover_image": row[3]} for row in cursor.fetchall()]
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
    
    author = session["user"]
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT stories.id, stories.title, COUNT(chapters.id) as chapter_count
        FROM stories 
        LEFT JOIN chapters ON stories.id = chapters.story_id 
        WHERE stories.author_name = ? 
        GROUP BY stories.id
        ORDER BY stories.id DESC
    """, (author,))
    
    user_stories = cursor.fetchall()
    total_stories_count = len(user_stories)
    db.close()
    
    return render_template("dashboard.html", user=author, stories=user_stories, total_stories=total_stories_count)

@app.route("/create-story")
def create_story():
    if "user" not in session:
        return redirect("/")
    return render_template("createstory.html")

@app.route("/edit/<int:story_id>")
def edit_story(story_id):
    if "user" not in session:
        return redirect("/")
    return f"<h3>Edit page for story #{story_id} is under construction!</h3><a href='/dashboard'>Go back</a>"

@app.route("/delete-story/<int:story_id>", methods=["POST"])
def delete_story(story_id):
    if "user" not in session:
        return redirect("/")

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM chapters WHERE story_id = ?", (story_id,))
    cursor.execute("DELETE FROM stories WHERE id = ?", (story_id,))
    db.commit()
    db.close()
    return redirect("/dashboard")

# UPDATED: Accept and save the uploaded image file
@app.route("/chapter", methods=["GET", "POST"])
def chapter():
    if "user" not in session:
        return redirect("/")
    
    if request.method == "POST":
        cover_image_name = "default.png" # Fallback if no image uploaded
        
        # Save the file if it exists
        if 'cover' in request.files:
            file = request.files['cover']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cover_image_name = filename

        story_data = {
            "title": request.form.get("title"),
            "genre": request.form.get("genre"),
            "tags": request.form.get("tags"),
            "synopsis": request.form.get("synopsis"),
            "cover_image": cover_image_name # Pass filename to the next page
        }
        return render_template("chapter.html", story_data=story_data)
    
    return redirect("/create-story")

# UPDATED: Insert the cover_image filename into the database
@app.route("/publish", methods=["POST"])
def publish():
    if "user" not in session:
        return redirect("/")

    author = session["user"]
    title = request.form.get("title")
    genre = request.form.get("genre")
    tags = request.form.get("tags")
    synopsis = request.form.get("synopsis")
    cover_image = request.form.get("cover_image") # Retrieve filename from hidden input
    
    chap_number = request.form.get("chapter_number")
    chap_title = request.form.get("chapter_title")
    content = request.form.get("content")

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO stories (author_name, title, genre, tags, synopsis, cover_image) VALUES (?, ?, ?, ?, ?, ?)",
        (author, title, genre, tags, synopsis, cover_image)
    )
    story_id = cursor.lastrowid 
    
    cursor.execute(
        "INSERT INTO chapters (story_id, chapter_number, chapter_title, content) VALUES (?, ?, ?, ?)",
        (story_id, chap_number, chap_title, content)
    )
    db.commit()
    db.close()
    
    return redirect("/home") 

@app.route("/read/<int:story_id>")
def read_story(story_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT title, author_name, synopsis FROM stories WHERE id=?", (story_id,))
    story = cursor.fetchone()
    cursor.execute("SELECT chapter_number, chapter_title, content FROM chapters WHERE story_id=? ORDER BY chapter_number ASC", (story_id,))
    chapters = cursor.fetchall()
    db.close()
    if not story:
        return redirect("/home")
    return render_template("read.html", story=story, chapters=chapters)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)