from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()  


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    hobbies = db.Column(db.Text)
    credits = db.Column(db.Integer, default=0)
    destination = db.Column(db.String(100))  # career interest
    ideas = db.relationship('Idea', backref='student', lazy=True)
    products = db.relationship('Product', backref='student', lazy=True)
    subjects = db.relationship('StudentSubject', backref='student', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    block = db.Column(db.String(50))  # e.g. "A Block"

class StudentSubject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'))

class Idea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))


    