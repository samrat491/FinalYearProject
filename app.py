from flask import Flask, render_template, request, redirect, flash, session, url_for, jsonify
import oracledb
import os 
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

try:
    # IMPORTANT: Replace this path with the exact location where you extracted the Instant Client
    oracledb.init_oracle_client(lib_dir=r"C:\Users\dell\Downloads\instantclient-basic-windows.x64-19.30.0.0.0dbru\instantclient_19_30")
except Exception as err:
    print("Error initializing Oracle Client. Check your lib_dir path.")
    print(err)

app = Flask(__name__)
app.secret_key = "secretkey123"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Configure oracledb to fetch CLOB data as standard strings
oracledb.defaults.fetch_lobs = False

# Create a folder to store uploaded cover images
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 

def get_db():
    # Update to Oracle 11g XE connection
    dsn = oracledb.makedsn("localhost", 1521, service_name="XE")
    return oracledb.connect(user="FYP", password="96555", dsn=dsn)

def init_db():
    db = get_db()
    cursor = db.cursor()
    
    # Oracle doesn't support "IF NOT EXISTS", so we catch the ORA-00955 error
    def create_table(query):
        try:
            cursor.execute(query)
        except oracledb.DatabaseError as e:
            error, = e.args
            if error.code != 955: # 955 means "name is already used by an existing object"
                raise

    # 1. User Table
    create_table("""
        CREATE TABLE users(
            id NUMBER PRIMARY KEY,
            name VARCHAR2(255) NOT NULL,
            gender VARCHAR2(50),
            birthdate VARCHAR2(50),
            email VARCHAR2(255) UNIQUE NOT NULL,
            password VARCHAR2(255) NOT NULL
        )
    """)
    # 2. Stories Table
    create_table("""
        CREATE TABLE stories(
            id NUMBER PRIMARY KEY,
            author_name VARCHAR2(255),
            title VARCHAR2(255) NOT NULL,
            genre VARCHAR2(100),
            tags VARCHAR2(255),
            synopsis CLOB,
            cover_image VARCHAR2(255)
        )
    """)
    # 3. Chapters Table
    create_table("""
        CREATE TABLE chapters(
            id NUMBER PRIMARY KEY,
            story_id NUMBER,
            chapter_number NUMBER,
            chapter_title VARCHAR2(255),
            content CLOB,
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
    # Oracle 11g limitation: use ROWNUM instead of LIMIT
    cursor.execute("""
        SELECT * FROM (
            SELECT id, title, genre, cover_image FROM stories ORDER BY id DESC
        ) WHERE ROWNUM <= 8
    """)
    latest_stories = [{"id": row[0], "title": row[1], "genre": row[2], "cover_image": row[3]} for row in cursor.fetchall()]
    db.close()
    return render_template("home.html", user=user, latest_stories=latest_stories)

@app.route("/about")
def about():
    return render_template("aboutus.html", user=session.get("user"))

@app.route("/", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect("/dashboard")
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT name, password FROM users WHERE email=:email", {"email": email})
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
                """INSERT INTO users (id, name, gender, birthdate, email, password) 
                   VALUES (users_seq.NEXTVAL, :name, :gender, :birthdate, :email, :password)""",
                {"name": name, "gender": gender, "birthdate": birthdate, "email": email, "password": password}
            )
            db.commit()
            db.close()
            flash("Payment of 500 NPR successful! Account created.")
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
    
    # Oracle requires non-aggregated columns in the SELECT to be strictly grouped
    cursor.execute("""
        SELECT stories.id, stories.title, COUNT(chapters.id) as chapter_count, 0 as views_count -- Added 0 for display-only views
        FROM stories 
        LEFT JOIN chapters ON stories.id = chapters.story_id 
        WHERE stories.author_name = :author 
        GROUP BY stories.id, stories.title
        ORDER BY stories.id DESC
    """, {"author": author})
    
    user_stories = cursor.fetchall()
    total_stories_count = len(user_stories)
    db.close()
    
    return render_template("dashboard.html", user=author, stories=user_stories, total_stories=total_stories_count)

@app.route("/create-story")
def create_story():
    if "user" not in session:
        return redirect("/")
    return render_template("createstory.html")

@app.route("/edit/<int:story_id>", methods=["GET", "POST"])
def edit_story(story_id):
    if "user" not in session: return redirect("/")
    author = session["user"]
    db = get_db()
    cursor = db.cursor()

    # Explicit column selection so story[6] is guaranteed to be cover_image
    cursor.execute("""
        SELECT id, author_name, title, genre, tags, synopsis, cover_image 
        FROM stories WHERE id=:id AND author_name=:author
    """, {"id": story_id, "author": author})
    story = cursor.fetchone()
    
    if not story:
        db.close()
        return redirect("/dashboard")

    if request.method == "POST":
        title = request.form.get("title")
        genre = request.form.get("genre")
        tags = request.form.get("tags")
        synopsis = request.form.get("synopsis")
        
        cover_image_name = story[6] 
        
        if 'cover' in request.files:
            file = request.files['cover']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cover_image_name = filename

        cursor.execute("""
            UPDATE stories SET title=:title, genre=:genre, tags=:tags, synopsis=:synopsis, cover_image=:cover 
            WHERE id=:id
        """, {"title": title, "genre": genre, "tags": tags, "synopsis": synopsis, "cover": cover_image_name, "id": story_id})
        db.commit()
        flash("Story updated successfully!")
        return redirect(f"/edit/{story_id}")

    cursor.execute("SELECT id, chapter_number, chapter_title FROM chapters WHERE story_id=:id ORDER BY chapter_number ASC", {"id": story_id})
    chapters = cursor.fetchall()
    db.close()
    
    return render_template("edit.html", story=story, chapters=chapters)

@app.route("/edit-chapter/<int:chapter_id>", methods=["GET", "POST"])
def edit_chapter(chapter_id):
    if "user" not in session: return redirect("/")
    db = get_db()
    cursor = db.cursor()
    
    # Selected explicit columns to maintain index compatibility with frontend
    cursor.execute("""
        SELECT chapters.id, chapters.story_id, chapters.chapter_number, chapters.chapter_title, chapters.content, stories.title 
        FROM chapters 
        JOIN stories ON chapters.story_id = stories.id 
        WHERE chapters.id = :id AND stories.author_name = :author
    """, {"id": chapter_id, "author": session["user"]})
    chapter = cursor.fetchone()
    
    if not chapter:
        db.close()
        return redirect("/dashboard")
        
    story_id = chapter[1]

    if request.method == "POST":
        chap_number = request.form.get("chapter_number")
        chap_title = request.form.get("chapter_title")
        content = request.form.get("content")
        
        cursor.execute("""
            UPDATE chapters SET chapter_number=:chap_num, chapter_title=:chap_title, content=:content WHERE id=:id
        """, {"chap_num": chap_number, "chap_title": chap_title, "content": content, "id": chapter_id})
        db.commit()
        db.close()
        return redirect(f"/edit/{story_id}")
        
    db.close()
    return render_template("edit_chapter.html", chapter=chapter)

@app.route("/add-chapter/<int:story_id>", methods=["GET", "POST"])
def add_chapter(story_id):
    if "user" not in session: return redirect("/")
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT id, title FROM stories WHERE id=:id AND author_name=:author", {"id": story_id, "author": session["user"]})
    story = cursor.fetchone()
    if not story: return redirect("/dashboard")

    if request.method == "POST":
        chap_number = request.form.get("chapter_number")
        chap_title = request.form.get("chapter_title")
        content = request.form.get("content")
        
        cursor.execute("""
            INSERT INTO chapters (id, story_id, chapter_number, chapter_title, content) 
            VALUES (chapters_seq.NEXTVAL, :story_id, :chap_num, :chap_title, :content)
        """, {"story_id": story_id, "chap_num": chap_number, "chap_title": chap_title, "content": content})
        db.commit()
        db.close()
        return redirect(f"/edit/{story_id}")

    cursor.execute("SELECT MAX(chapter_number) FROM chapters WHERE story_id=:id", {"id": story_id})
    max_chap = cursor.fetchone()[0]
    next_chap = (max_chap or 0) + 1
    db.close()
    
    return render_template("add_chapter.html", story=story, next_chap=next_chap)

@app.route("/delete-story/<int:story_id>", methods=["POST"])
def delete_story(story_id):
    if "user" not in session:
        return redirect("/")

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM chapters WHERE story_id = :id", {"id": story_id})
    cursor.execute("DELETE FROM stories WHERE id = :id", {"id": story_id})
    db.commit()
    db.close()
    return redirect("/dashboard")

@app.route("/chapter", methods=["GET", "POST"])
def chapter():
    if "user" not in session:
        return redirect("/")
    
    if request.method == "POST":
        cover_image_name = "default.png" 
        
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
            "cover_image": cover_image_name 
        }
        return render_template("chapter.html", story_data=story_data)
    
    return redirect("/create-story")

@app.route("/publish", methods=["POST"])
def publish():
    if "user" not in session:
        return redirect("/")

    author = session["user"]
    title = request.form.get("title")
    genre = request.form.get("genre")
    tags = request.form.get("tags")
    synopsis = request.form.get("synopsis")
    cover_image = request.form.get("cover_image") 
    
    chap_number = request.form.get("chapter_number")
    chap_title = request.form.get("chapter_title")
    content = request.form.get("content")

    db = get_db()
    cursor = db.cursor()
    
    # 1. Insert Story using Sequence
    cursor.execute("""
        INSERT INTO stories (id, author_name, title, genre, tags, synopsis, cover_image) 
        VALUES (stories_seq.NEXTVAL, :author, :title, :genre, :tags, :synopsis, :cover)
    """, {"author": author, "title": title, "genre": genre, "tags": tags, "synopsis": synopsis, "cover": cover_image})
    
    # 2. Fetch last inserted ID using CURRVAL
    cursor.execute("SELECT stories_seq.CURRVAL FROM dual")
    story_id = cursor.fetchone()[0]
    
    # 3. Insert Chapter using Sequence
    cursor.execute("""
        INSERT INTO chapters (id, story_id, chapter_number, chapter_title, content) 
        VALUES (chapters_seq.NEXTVAL, :story_id, :chap_num, :chap_title, :content)
    """, {"story_id": story_id, "chap_num": chap_number, "chap_title": chap_title, "content": content})
    
    db.commit()
    db.close()
    
    return redirect("/home") 

@app.route("/read/<int:story_id>")
def read_story(story_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT title, author_name, synopsis FROM stories WHERE id=:id", {"id": story_id})
    story = cursor.fetchone()
    cursor.execute("SELECT chapter_number, chapter_title, content FROM chapters WHERE story_id=:id ORDER BY chapter_number ASC", {"id": story_id})
    chapters = cursor.fetchall()
    db.close()
    if not story:
        return redirect("/home")
    return render_template("read.html", story=story, chapters=chapters)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/search")
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    db = get_db()
    cursor = db.cursor()
    # Using bind variables and wildcards for partial matches (case-insensitive)
    search_term = f"%{query}%"
    cursor.execute("""
        SELECT * FROM (
            SELECT id, title FROM stories WHERE LOWER(title) LIKE LOWER(:term) ORDER BY id DESC
        ) WHERE ROWNUM <= 5
    """, {"term": search_term})
    
    results = [{"id": row[0], "title": row[1]} for row in cursor.fetchall()]
    db.close()
    return jsonify(results)

@app.route("/filter")
def filter_stories():
    db = get_db()
    cursor = db.cursor()
    
    # Retrieve selected tags from the query string parameters
    tags_str = request.args.get("tags", "")
    selected_tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    
    stories = []
    searched = False
    
    # Execute the query if any tags are selected
    if selected_tags:
        searched = True
        query = "SELECT id, title, genre, cover_image FROM stories WHERE 1=1"
        params = {}
        
        for i, tag in enumerate(selected_tags):
            param_name = f"tag{i}"
            query += f" AND LOWER(tags) LIKE LOWER(:{param_name})"
            params[param_name] = f"%{tag}%"

        query += " ORDER BY id DESC"
        
        cursor.execute(query, params)
        stories = [{"id": row[0], "title": row[1], "genre": row[2], "cover_image": row[3]} for row in cursor.fetchall()]
    elif 'tags' in request.args: # If search was clicked with no tags
        searched = True

    db.close()
    return render_template("filter.html", user=session.get("user"), stories=stories, searched=searched, current_tags=selected_tags)

if __name__ == "__main__":
    app.run(debug=True)