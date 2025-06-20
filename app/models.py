from app import app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String


import pymysql
pymysql.install_as_MySQLdb()
from flask_sqlalchemy import SQLAlchemy

app.db = SQLAlchemy(app)

class User(app.db.Model):
    __tablename__ = "users"
    id    = Column(Integer, primary_key = True)
    login = Column(String(20), unique=True)

with app.app_context():
    app.db.create_all()
