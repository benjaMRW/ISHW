from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)  # Required for tutor contact
    hobbies = db.Column(db.Text)
    destination = db.Column(db.String(100))  # career interest
    ideas = db.relationship('Idea', backref='student', lazy=True)
    products = db.relationship('Product', backref='student', lazy=True)
    tutor = db.relationship('Tutor', backref='student', uselist=False, lazy=True)

class Idea(db.Model):
    __tablename__ = 'idea'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))

class Tutor(db.Model):
    __tablename__ = 'tutor'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), unique=True, nullable=False)
    subjects = db.Column(db.Text)  # Comma-separated subjects (e.g., "Math,Physics")
    year = db.Column(db.Integer)  # Academic year (e.g., 1, 2, 3, 4)