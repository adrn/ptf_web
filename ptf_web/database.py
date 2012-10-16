# Standard Library
import logging
import re
import os, sys
import glob
import sqlite3
from datetime import datetime
import cPickle as pickle

# Third party
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, \
     ForeignKey
from sqlalchemy.orm import scoped_session, sessionmaker, backref, relation
from sqlalchemy.ext.declarative import declarative_base
import pymongo

from flask import url_for, Markup
import numpy as np
from ptf_web import app
from ptf.globals import config

engine = create_engine(app.config['DATABASE_URI'],
                       convert_unicode=True,
                       **app.config['DATABASE_CONNECT_OPTIONS'])
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

def init_user_db():
    Model.metadata.create_all(bind=engine)

Model = declarative_base(name='Model')
Model.query = db_session.query_property()

class User(Model):
    __tablename__ = 'users'
    id = Column('user_id', Integer, primary_key=True)
    openid = Column('openid', String(200))
    name = Column(String(200))
    email = Column(String(200))

    def __init__(self, name, openid, email):
        self.name = name
        self.openid = openid
        self.email = email

    def to_json(self):
        return dict(name=self.name, is_admin=self.is_admin, email=self.email)

    @property
    def is_admin(self):
        return self.openid in app.config['ADMINS']

    def __eq__(self, other):
        return type(self) is type(other) and self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

class OpenIDAssociation(Model):
    __tablename__ = 'openid_associations'
    id = Column('association_id', Integer, primary_key=True)
    server_url = Column(String(1024))
    handle = Column(String(255))
    secret = Column(String(255))
    issued = Column(Integer)
    lifetime = Column(Integer)
    assoc_type = Column(String(64))


class OpenIDUserNonce(Model):
    __tablename__ = 'openid_user_nonces'
    id = Column('user_nonce_id', Integer, primary_key=True)
    server_url = Column(String(1024))
    timestamp = Column(Integer)
    salt = Column(String(40))

def init_db():
    init_user_db()

# ---
# END SQL SHIT FOR USERS
# ---

connection = pymongo.Connection(config["db_address"], config["db_port"])
ptf = connection.ptf # the database
ptf.authenticate(config["www_db_user"], config["www_db_password"])
#light_curve_collection = ptf.light_curves
#candidate_status_collection = ptf.candidate_status
light_curve_collection = ptf.light_curves
field_collection = ptf.fields
table_state_collection = ptf.table_state

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    init_db()
