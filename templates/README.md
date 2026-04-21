# 📖 FPY Project - Web Novel & Story Publishing Platform

Welcome to the **FPY Project**, a comprehensive full-stack web application designed for writers and readers of web novels and serialized stories. Built with a robust **Python (Flask)** backend and powered by an **Oracle Database**, this platform provides a seamless experience for publishing, reading, and managing literary content.

Whether you're an author looking to track your story's performance or a reader wanting a distraction-free environment with customizable themes, this platform has you covered.

---

## ✨ Core Features

### 📝 For Authors
- **Intuitive Dashboard:** A central hub to manage your published stories, track the total number of uploaded chapters, and monitor accumulated reader views.
- **Comprehensive Story Management:** 
  - Upload custom cover images (saved locally with secure filenames).
  - Categorize stories with a primary Genre (e.g., Fantasy, Action, Mystery).
  - Apply up to 10 popular Tags (e.g., "Sword and Sorcery", "Transmigration", "Overpowered Hero") for better discoverability.
- **Distraction-Free Chapter Editor:** A dedicated writing interface featuring a live word counter and dynamic theme switching (Cozy Light Mode / Dark Mode) to reduce eye strain during long writing sessions.
- **Edit & Update:** Easily modify story metadata, replace cover images, or edit previously published chapter content at any time.

### 📖 For Readers
- **Modern Reader Interface:** Inspired by top e-reading applications, the reader view includes:
  - **Dynamic Typography:** Instantly increase (A+) or decrease (A-) font sizes.
  - **Tri-Theme Support:** Toggle between Clean Light, Warm Sepia, and Pure Dark reading modes.
  - **Seamless Navigation:** Jump between chapters using a dropdown menu or quick "Next/Previous" buttons.
  - **Auto-Hiding Navbar:** The top navigation bar hides smoothly while scrolling down to maximize reading space.
- **Live Search & Discovery:** 
  - Search stories instantly from the navbar with an AJAX-powered live dropdown.
  - Explore the "Latest Updates" grid or browse the "Trending This Week" sidebar.
- **Advanced Filtering:** A dedicated filter page allowing readers to find stories by selecting specific, multi-match tags.
- **Global Dark/Light Mode:** A persistent UI theme toggle that saves user preference across the entire site via LocalStorage.

### 🛡️ Administration & Security
- **Secure Authentication:** Passwords are encrypted using `werkzeug.security` (PBKDF2 hashing) before database insertion.
- **Payment Gateway Integration:** Mock integration with **Khalti Payment Gateway** during user registration, featuring a custom interactive modal for OTP and MPIN validation.
- **Master Admin Dashboard:** Accessible via a hardcoded master email (`sangamp607@gmail.com`).
- **User Moderation:** Admins can view detailed statistics of all registered users, inspect their published catalogs, and perform cascade deletions (automatically wiping the user's chapters, stories, and account securely).

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | Python 3, Flask |
| **Database** | Oracle Database (11g XE / 19c) via `oracledb` |
| **Frontend Markup** | HTML5, Jinja2 Templating |
| **Frontend Styling** | CSS3 (Flexbox, CSS Grid, Custom Variables) |
| **Frontend Logic** | Vanilla JavaScript (ES6), AJAX (Fetch API) |
| **Security** | Werkzeug Security (Password Hashing) |

---

## 🗄️ Oracle Database Architecture

The platform leverages an Oracle Relational Database. Notably, the application utilizes Oracle **Sequences** (`users_seq`, `stories_seq`, `chapters_seq`) for auto-incrementing Primary Keys and handles large text data using **CLOB** (Character Large Object) types.

### 1. `users`
Stores registered reader and author accounts.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | NUMBER | PRIMARY KEY | Unique identifier (via `users_seq`) |
| `name` | VARCHAR2(255) | NOT NULL | Full name |
| `gender` | VARCHAR2(50) | | User's gender |
| `birthdate` | VARCHAR2(50) | | Date of birth |
| `email` | VARCHAR2(255) | UNIQUE, NOT NULL | Login email |
| `password` | VARCHAR2(255) | NOT NULL | Hashed password |

### 2. `stories`
Stores metadata for novels published on the platform.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | NUMBER | PRIMARY KEY | Unique identifier (via `stories_seq`) |
| `author_name` | VARCHAR2(255) | | Author's name (References `users.name`) |
| `title` | VARCHAR2(255) | NOT NULL | Story title |
| `genre` | VARCHAR2(100) | | Primary genre |
| `tags` | VARCHAR2(255) | | Comma-separated tags |
| `description` | CLOB | | Detailed story synopsis |
| `cover_image` | VARCHAR2(255)| | Filename of the uploaded cover image |
| `views` | NUMBER | DEFAULT 0 | Total accumulated reads |

### 3. `chapters`
Stores individual serialized chapters linked to a parent story.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | NUMBER | PRIMARY KEY | Unique identifier (via `chapters_seq`) |
| `story_id` | NUMBER | FOREIGN KEY | Links back to `stories.id` |
| `chapter_number`| NUMBER | | Chronological order |
| `chapter_title` | VARCHAR2(255) | | Title of the chapter |
| `content` | CLOB | | The rich text/body of the chapter |

---

## 📂 Directory Structure

```text
FPY project/
│
├── app.py                      # Core Python backend, routing, and DB logic
│
├── static/
│   ├── style.css               # Massive global stylesheet handling all UI/UX
│   ├── images/                 # Static assets (placeholders, logos)
│   └── uploads/                # Directory for user-uploaded cover images
│
└── templates/                  # Jinja2 HTML Views
    ├── home.html               # Dynamic landing page (Latest Updates, Search)
    ├── read.html               # Custom Reader Engine (Themes, Font scaling)
    ├── createstory.html        # Multi-step story publication flow
    ├── chapter.html            # Chapter editor with live word counter
    ├── dashboard.html          # Author's management console
    ├── edit.html               # Interface to modify story details
    ├── filter.html             # Tag-based search and filter engine
    ├── admin.html              # Master admin control panel
    ├── login.html              # User authentication entry
    ├── register.html           # Registration with Khalti Payment UI
    └── README.md               # This documentation file
```

---

## ⚙️ Local Setup & Installation

### 1. Prerequisites
- Python 3.x installed.
- Oracle Database (11g XE or higher) installed and running locally.
- Oracle Instant Client downloaded and extracted.

### 2. Install Dependencies
Navigate to the project directory and install the required Python packages:
```bash
pip install Flask oracledb werkzeug
```

### 3. Database Configuration
1. Ensure your Oracle Database is running on `localhost:1521` with service name `XE`.
2. Ensure a database user exists with the username `FYP` and password `96555`.
3. Update the `lib_dir` path in `app.py` to point to your local Oracle Instant Client directory:
   ```python
   oracledb.init_oracle_client(lib_dir=r"C:\Path\To\Your\instantclient")
   ```

### 4. Running the Application
Start the Flask development server:
```bash
python app.py
```
Access the application in your browser at `http://127.0.0.1:5000/`.

### 5. Default Admin Access
To access the admin dashboard, register or login with the hardcoded admin email:
- **Email:** `sangamp607@gmail.com`