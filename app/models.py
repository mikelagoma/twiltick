from app import app
from app import db
from hashlib import md5

import sys
import re

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(16), index=True, unique=True)
    email = db.Column(db.String(120), index=True)
    lastsymbol = db.Column(db.String(120))
    messages = db.relationship('Message', backref='sender', lazy='dynamic')
    subscriptions = db.relationship('Subscription', backref='subscriber', lazy='dynamic')

    def __repr__(self):
        return '<User %r>' % (self.phone)

class Message(db.Model):
    __searchable__ = ['body']

    id = db.Column(db.Integer, primary_key = True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    language = db.Column(db.String(5))

    def __repr__(self):
        return '<Message %r>' % (self.body)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    symbol = db.Column(db.String(5))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Subscription %r, %r>' % (self.user_id, self.symbol)

