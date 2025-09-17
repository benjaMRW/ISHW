"""
Main Flask application for Burnside High School support website.

This app provides routes for:
- User authentication (login, logout, register, profile)
- Tutor listings
- Campus map visualization with Folium
- Notices and feedback
- AI chatbot using LlamaIndex
"""

import os
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from werkzeug.security import check_password_hash  # for secure password handling
from flask_sqlalchemy import SQLAlchemy
import feedparser
import folium
import re
from markupsafe import escape
from app.models import db, Student, Idea, Product, Tutor
from llama_index.core import (
    VectorStoreIndex, SimpleDirectoryReader,
    StorageContext, load_index_from_storage
)
import openai  # ensure installed: pip install openai


# Load environment variables (important for security)
load_dotenv()

# Initialize Flask app
from app import app  # why: app instance is shared across modules for consistency

# Security key → should be in environment vars in production
app.secret_key = "1234"

# Database config (SQLite for dev; can be swapped to PostgreSQL/MySQL later)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///student.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# OpenAI API key setup
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------
# LlamaIndex setup for chatbot
# -------------------------------
if os.path.exists("index_store"):
    # why: re-use existing index for speed and persistence
    storage_context = StorageContext.from_defaults(persist_dir="index_store")
    index = load_index_from_storage(storage_context)
else:
    # because: if no saved index exists, create it fresh from docs
    documents = SimpleDirectoryReader("app/docs").load_data()
    index = VectorStoreIndex.from_documents(documents)
    index.storage_context.persist("index_store")

query_engine = index.as_query_engine()


# -------------------------------
# Routes
# -------------------------------

@app.route("/chat", methods=["GET", "POST"])
def chatbot():
    """
    Chatbot route where students can ask questions
    and get AI-generated responses from LlamaIndex.
    """
    answer = ""
    if request.method == "POST":
        question = request.form["question"]
        response = query_engine.query(question)  # why: offloads NLP to index
        answer = str(response)
    return render_template("chat.html", answer=answer)


@app.route("/")
def home():
    """Home page with navigation to features."""
    return render_template("home.html", page_title="Home")


@app.route("/profile")
def profile():
    """Student profile page (requires login)."""
    if "student_number" not in session:
        return redirect("/login")  # because: only logged-in users can view

    student = Student.query.filter_by(
        student_number=session["student_number"]
    ).first()
    return render_template("profile.html", student=student)


@app.route("/career")
def career():
    """Career guidance page."""
    return render_template("career.html", page_title="Career")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login route for students.
    Currently uses plain-text password (to be improved with hashing).
    How:
    - GET request → just shows the login form.
    - POST request → retrieves form data, looks up the student in the DB.
    - If a match is found, student info is stored in Flask session so it
      can be accessed across routes (e.g. profile, feedback).
    - If no match, sets an error flag so the template can display a warning.
    """
    error = False
    if request.method == "POST":
        student_number = request.form["student_number"]
        password = request.form["password"]

        # why: direct filter simplifies check, but unsafe in real-world
        student = Student.query.filter_by(
            student_number=student_number, password=password
        ).first()

        if student:
            # because: store minimal info in session for later use
            session["student_number"] = student.student_number
            session["name"] = student.name
            return redirect("/")
        error = True

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """Logout and clear session."""
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Register new students and tutors.
    Tutors require extra fields (subjects, year).
    """
    alreadyexist = False
    if request.method == "POST":
        student_number = request.form["student_number"].strip()
        password = request.form["password"].strip()
        name = (
            request.form["student_name"].strip() + " " +
            request.form.get("student_lastname", "").strip()
        )
        email = request.form["email"].strip()
        is_tutor = request.form.get("is_tutor") == "on"
        subjects = request.form.get("subjects").strip() if is_tutor else None
        year = request.form.get("year").strip() if is_tutor else None

        # Strip HTML tags and escape
        def sanitize(text, max_words=50, max_chars=200):
            text = re.sub(r"<[^>]*>", "", text)  # remove HTML tags
            text = escape(text)  # escape unsafe characters
            if len(text.split()) > max_words:
                return None
            if len(text) > max_chars:
                return None
            return text

        student_number = sanitize(student_number, max_words=1, max_chars=20)
        password = sanitize(password, max_words=1, max_chars=50)
        name = sanitize(name, max_words=10, max_chars=100)
        email = sanitize(email, max_words=1, max_chars=100)
        subjects = sanitize(subjects, max_words=20, max_chars=200) if subjects else None
        year = sanitize(year, max_words=1, max_chars=4) if year else None

        if not student_number or not password or not name or not email:
            flash("Invalid input: please check your details.", "error")
            return render_template("register.html", page_title="Register", alreadyexist=alreadyexist)

        existing_student = Student.query.filter_by(student_number=student_number).first()

        if existing_student:
            alreadyexist = True
        else:
            if is_tutor and (not subjects or not year):
                flash("Please provide subjects and year for tutor registration.", "error")
                return render_template(
                    "register.html",
                    page_title="Register",
                    alreadyexist=alreadyexist
                )

            new_student = Student(
                student_number=student_number,
                password=password,  # ⚠️ TODO: hash passwords
                name=name.strip(),
                email=email
            )
            db.session.add(new_student)
            db.session.commit()

            if is_tutor:
                tutor = Tutor(
                    student_id=new_student.id,
                    subjects=subjects,
                    year=year
                )
                db.session.add(tutor)
                db.session.commit()

            # auto-login after registration
            session["student_number"] = student_number
            session["name"] = name.strip()
            return redirect(url_for("home"))

    return render_template(
        "register.html", page_title="Register", alreadyexist=alreadyexist
    )


@app.route("/tutors")
def tutors():
    """List all registered tutors."""
    all_tutors = Tutor.query.all()
    return render_template("tutors.html", tutors=all_tutors, page_title="Available Tutors")


@app.route("/student")
def students():
    """Static student info page."""
    return render_template("student.html", page_title="Home")


@app.route("/subjects")
def subjects():
    """Subjects overview page."""
    return render_template("subjects.html", page_title="Home")


# Default map center (school midpoint)
SCHOOL_CENTER = [-43.50713855170288, 172.57701091063876]

# Dictionary of campus locations and their coordinates
# Why: defines all key points students may want to navigate to
# How: keys are location names, values are [lat, lon] lists
LOCATIONS = {
    "A Block": [-43.50767607962358, 172.57621966007108],
    "B Block": [-43.507258002762555, 172.57649534465384],
    "C1 Block": [-43.507336958220584, 172.57692885310962],
    "C3-4 Block": [-43.50713855170288, 172.57701091063876],
    "P Block": [-43.50679524519272, 172.57576170047136],
    "M Block": [-43.508036322773854, 172.57585920976163],
    "Aurora Center": [-43.508548336966456, 172.57611858764898],
    "Library": [-43.50768093385897, 172.57690035175943],
    "G Block": [-43.50680754991145, 172.57687446294506],
    "L Block": [-43.50729540052514, 172.57605599645274],
    "N Block": [-43.50672110583437, 172.57630225157354],
    "E Block": [-43.50743157630898, 172.57557856325985],
    "K5-K6 Block": [-43.50599959130328, 172.5766635615753],
    "K1-K3 Block": [-43.5062665985537, 172.57640539896025],
    "Hunter Gym": [-43.50632638862487, 172.57709402902427],
    "Cross Gym": [-43.50673346447026, 172.57777757004496],
    "Dance Hall": [-43.50622379965693, 172.57682248245672],
    "Canteen": [-43.50739087991838, 172.57747902572711],
    "Pool": [-43.50698842492684, 172.57770103373863],
    "Turf/Football-Field": [-43.506852653812025, 172.57802912691722],
    "D1-D6 Block": [-43.50773718242374, 172.57730998413808],
    "D13-D16 Block": [-43.50761170681216, 172.57759832158754],
    "X Block": [-43.50696927145228, 172.57637389795957],
    "IT Office": [-43.50718642257362, 172.57605667843748],
    "Career Office": [-43.5068786061543, 172.5770557109524],
}


@app.route("/map")
def map_view():
    """
    Interactive campus map using Folium.

    Why:
        Helps students locate school facilities visually.

    How:
        - Creates a folium map centered at SCHOOL_CENTER
        - Loops over LOCATIONS dictionary
        - Chooses a color per category (sports, common, office, block)
        - Places styled circular markers with first letter of name
        - Fits map bounds to include all markers
        - Renders HTML map into template
    """

    # Extract query params for navigation (optional future use)
    start_name = request.args.get("start", "").strip().title()
    destination_name = request.args.get("destination", "").strip().title()

    # Initialize folium map
    m = folium.Map(
        location=SCHOOL_CENTER,
        zoom_start=18,
        tiles="CartoDB positron",
        zoom_control=False,
        attributionControl=False,
    )

    # Add location markers
    for name, coords in LOCATIONS.items():
        # Default: academic blocks = green
        icon_color = "#00a86b"

        # Sports facilities = red
        if "Gym" in name or "Pool" in name or "Turf" in name:
            icon_color = "#ff6b6b"

        # Common areas (library, canteen, centers) = blue
        elif "Library" in name or "Canteen" in name or "Center" in name:
            icon_color = "#4d79ff"

        # Offices = yellow
        elif "IT Office" in name or "Career Office" in name:
            icon_color = "#fffc4f"

        # Create styled marker with first letter of name
        folium.Marker(
            location=coords,
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    background: {icon_color};
                    border: 2px solid white;
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                ">
                    {name[0]}
                </div>
                """
            ),
            tooltip=name,
        ).add_to(m)

    # Adjust map bounds to fit all markers
    sw = [
        min(lat for lat, lon in LOCATIONS.values()),
        min(lon for lat, lon in LOCATIONS.values()),
    ]
    ne = [
        max(lat for lat, lon in LOCATIONS.values()),
        max(lon for lat, lon in LOCATIONS.values()),
    ]
    m.fit_bounds([sw, ne], padding=(80, 80))

    # Return map to template
    return render_template(
        "map.html",
        map_html=m._repr_html_(),
        page_title="Campus Map",
        locations=LOCATIONS,
    )


@app.route("/notices")
def notices():
    """Fetch and display school notices via RSS feed."""
    notices_data = get_school_notices()
    return render_template("notices.html", notices=notices_data)


def get_school_notices():
    """Helper function to parse RSS notices."""
    try:
        feed = feedparser.parse("https://burnside.school.kiwi/rss")
        if feed.bozo:
            print("Failed to parse feed:", feed.bozo_exception)
            return []

        notices = []
        for entry in feed.entries[:40]:
            notices.append({
                "title": entry.get("title", "No title"),
                "date": entry.get("published", "No date"),
                "content": entry.get("description", "No content"),
            })
        return notices
    except Exception as e:
        print(f"Error fetching notices: {str(e)}")
        return []


import re
from markupsafe import escape

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    """Submit and view student feedback/ideas."""
    if request.method == "POST":
        student_number = request.form.get("student_number")
        feedback_content = request.form.get("feedback")

        # Validate input presence
        if not student_number or not feedback_content:
            flash("Please provide both student number and feedback.", "error")
            return render_template("ideas.html", page_title="Feedback")

        # Strip HTML tags (basic sanitation)
        feedback_content = re.sub(r"<[^>]*>", "", feedback_content)

        # Escape unsafe characters (extra safety)
        feedback_content = escape(feedback_content)

        # Limit feedback length (e.g., 150 words or 1000 chars)
        word_limit = 150
        char_limit = 1000

        if len(feedback_content.split()) > word_limit:
            flash(f"Feedback too long. Please limit to {word_limit} words.", "error")
            return render_template("ideas.html", page_title="Feedback")

        if len(feedback_content) > char_limit:
            flash(f"Feedback too long. Please limit to {char_limit} characters.", "error")
            return render_template("ideas.html", page_title="Feedback")

        # Validate student exists
        student = Student.query.filter_by(student_number=student_number).first()
        if not student:
            flash("Invalid student number. Please try again.", "error")
            return render_template("ideas.html", page_title="Feedback")

        # Save feedback
        new_feedback = Idea(
            student_id=student.id,
            content=feedback_content,
            timestamp=datetime.utcnow()
        )

        try:
            db.session.add(new_feedback)
            db.session.commit()
            flash("Feedback submitted successfully!", "success")
            return redirect(url_for("feedback"))
        except Exception:
            db.session.rollback()
            flash("An error occurred while submitting feedback. Please try again.", "error")

    feedbacks = Idea.query.order_by(Idea.timestamp.desc()).all()
    return render_template("ideas.html", page_title="Feedback", feedbacks=feedbacks)



@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 error page."""
    return render_template("404.html", page_title="Page Not Found"), 404


if __name__ == "__main__":
    app.run(debug=True)
