from app import app
from flask import Flask, render_template, request, redirect, url_for, session, flash, sessions 
from werkzeug.security import check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
import requests 
from bs4 import BeautifulSoup  
from datetime import datetime, time
import feedparser
import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
from webdriver_manager.chrome import ChromeDriverManager
import folium
from folium.plugins import Search
from app.models import db, Student, Subject, StudentSubject, Idea, Product




app.secret_key = '1234'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///student.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


@app.route('/')
def home():
    return render_template('home.html', page_title='Home')

@app.route('/profile')
def profile():
    if 'student_number' not in session:
        return redirect('/login')  # must be logged in

    # Get the student info from the database
    student = Student.query.filter_by(student_number=session['student_number']).first()

    return render_template('profile.html', student=student)


@app.route('/career')
def car():
    return render_template('career.html', page_title='carrer')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_number = request.form['student_number']
        password = request.form['password']

        student = Student.query.filter_by(student_number=student_number, password=password).first()

        if student:
            session['student_number'] = student.student_number
            session['name'] = student.name
            return redirect('/')
        else:
            error = True
    return render_template('login.html', error=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/register', methods=['GET', 'POST'])
def reg():
    alreadyexist = False

    if request.method == 'POST':
        student_number = request.form['student_number']
        password = request.form['password']
        name = request.form['student_name']
        email = request.form['email']
        # Check if student number already exists
        existing_student = Student.query.filter_by(student_number=student_number).first()

        if existing_student:
            alreadyexist = True
        else:
            # Create and save the student
            new_student = Student(student_number=student_number, password=password, name=name, email=email)
            db.session.add(new_student)
            db.session.commit()

            # Log them in
            session['student_number'] = student_number
            session['name'] = name

            return redirect(url_for('home'))

    return render_template('register.html', page_title='Register', alreadyexist=alreadyexist)


  



@app.route('/student')
def students():
    return render_template('student.html', page_title='Home')


@app.route('/subjects')
def subjects():
    return render_template('subjects.html', page_title='Home')



@app.route('/map')
def map():
    start_name = request.args.get('start', '').strip().title()
    destination_name = request.args.get('destination', '').strip().title()

    SCHOOL_CENTER = [-43.50713855170288, 172.57701091063876]

    locations = {
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
        "X Block": [-43.50696927145228, 172.57637389795957]
    }

    m = folium.Map(
        location=SCHOOL_CENTER,
        zoom_start=18,
        tiles='CartoDB positron',
        zoom_control=False,  # We'll add custom controls
        attributionControl=False
    )

    # Add all location markers with enhanced styling
    for name, coords in locations.items():
        # Determine icon color based on location type
        icon_color = '#00a86b'  # Default green for academic blocks
        if 'Gym' in name or 'Pool' in name or 'Turf' in name:
            icon_color = '#ff6b6b'  # Red for sports facilities
        elif 'Library' in name or 'Canteen' in name or 'Center' in name:
            icon_color = '#4d79ff'  # Blue for common areas
            
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
            tooltip=name
        ).add_to(m)
        
    sw = [min(lat for lat, lon in locations.values()), min(lon for lat, lon in locations.values())]
    ne = [max(lat for lat, lon in locations.values()),  max(lon for lat, lon in locations.values())]
    m.fit_bounds([sw, ne], padding=(80, 80))  # Add 50px padding
    


    return render_template('map.html', map_html=m._repr_html_(), page_title='Campus Map', locations=locations)




@app.route('/notices')
def notices():
    notices_data = get_school_notices()
    return render_template('notices.html', notices=notices_data)



def get_school_notices():
    try:
        feed = feedparser.parse("https://burnside.school.kiwi/rss")
        if feed.bozo:
            print("Failed to parse feed:", feed.bozo_exception)
            return []
        
        notices = []
        for entry in feed.entries[:40]:
            notices.append({
                'title': entry.get('title', 'No title'),
                'date': entry.get('published', 'No date'),
                'content': entry.get('description', 'No content')
            })
        return notices
    except Exception as e:
        print(f"Error fetching notices: {str(e)}")
        return []


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        student_number = request.form.get('student_number')
        feedback_content = request.form.get('feedback')

        # Validate input
        if not student_number or not feedback_content:
            flash('Please provide both student number and feedback.', 'error')
            return render_template('ideas.html', page_title='Feedback')

        # Find the student by student_number
        student = Student.query.filter_by(student_number=student_number).first()
        if not student:
            flash('Invalid student number. Please try again.', 'error')
            return render_template('ideas.html', page_title='Feedback')

        # Create and save the new feedback
        new_feedback = Idea(student_id=student.id, content=feedback_content, timestamp=datetime.utcnow())
        try:
            db.session.add(new_feedback)
            db.session.commit()
            flash('Feedback submitted successfully!', 'success')
            return redirect(url_for('feedback'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while submitting feedback. Please try again.', 'error')

    # For GET request, fetch all feedback to display (optional)
    feedbacks = Idea.query.order_by(Idea.timestamp.desc()).all()
    return render_template('ideas.html', page_title='Feedback', feedbacks=feedbacks)

if __name__ == '__main__':
    app.run(debug=True)