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

from flask import url_for, Markup
import numpy as np
from ptf_web import app

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

lc_engine = create_engine(app.config['LIGHT_CURVE_DATABASE_URI'],
                       convert_unicode=True,
                       **app.config['LIGHT_CURVE_DATABASE_CONNECT_OPTIONS'])
lc_db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=lc_engine))

lc_Model = declarative_base(name="lc_Model")
lc_Model.query = lc_db_session.query_property()

class LightCurve(lc_Model):
    __tablename__ = 'light_curve'
    
    #(source_id int, field_id int, ra real, dec real, looked_at int, obj_type text
    
    pk = Column("pk", Integer, primary_key=True)
    matchedSourceID = Column('matchedSourceID', Integer)
    field_id = Column('field_id', Integer)
    ccd_id = Column('ccd_id', Integer)
    ra = Column('ra', Float)
    dec = Column('dec', Float)
    obj_type = Column('obj_type', String(40))
    
    def __init__(self, matchedSourceID, field_id, ccd_id, ra, dec, obj_type):
        self.matchedSourceID = matchedSourceID
        self.field_id = field_id
        self.ccd_id = ccd_id
        self.ra = ra
        self.dec = dec
        self.obj_type = obj_type
        
    def to_json(self):
        return dict(matchedSourceID=self.matchedSourceID, \
                    field_id=self.field_id, \
                    ccd_id=self.ccd_id, \
                    ra=self.ra, \
                    dec=self.dec, \
                    obj_type=self.obj_type,\
                    num_obs=self.num_obs)
    @property
    def data(self):
        filename = os.path.join(app.config['LIGHT_CURVE_PATH'], "field{:06d}_ccd{:02d}_source{:06d}.pickle".format(self.field_id, self.ccd_id, self.matchedSourceID))
        f = open(filename)
        light_curve = pickle.load(f)
        f.close()
        #srt = np.argsort(all_data["mjd"])
        
        return dict(mjd=light_curve.mjd, 
                    mag=light_curve.mag,
                    error=light_curve.error)
    
    @property
    def num_obs(self):
        filename = os.path.join(app.config['LIGHT_CURVE_PATH'], "field{:06d}_ccd{:02d}_source{:06d}.pickle".format(self.field_id, self.ccd_id, self.matchedSourceID))
        f = open(filename)
        light_curve = pickle.load(f)
        f.close()
        
        return len(light_curve.exposures)
    
    def __eq__(self, other):
        if other is None:
            return False
        
        try:
            return self.matchedSourceID == other.matchedSourceID
        except AttributeError:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)


def init_light_curve_db():
    lc_Model.metadata.create_all(bind=lc_engine)

    for lc_file in glob.glob(os.path.join(app.config['LIGHT_CURVE_PATH'], "*.pickle")):
        try:
            f = open(lc_file)
            light_curve = pickle.load(f)
            f.close()
        except IOError:
            print "Unable to open light curve file: {}".format(lc_file)
            raise
        
        if lc_db_session.query(LightCurve).\
            filter(LightCurve.field_id == light_curve.field_id).\
            filter(LightCurve.matchedSourceID == light_curve.source_id).\
            filter(LightCurve.ccd_id == light_curve.ccd_id).count() == 0:
            lc_db_session.add(LightCurve(matchedSourceID=light_curve.source_id,\
                                         field_id=light_curve.field_id,\
                                         ccd_id=light_curve.ccd_id,\
                                         ra=light_curve.metadata["ra"],\
                                         dec=light_curve.metadata["dec"],\
                                         obj_type="")\
                              )
            lc_db_session.commit()
        else:
            logging.debug("Light curve {} already in database".format(light_curve.source_id))
    
    logging.info("Committing light curves")


def init_db():
    #init_user_db()
    init_light_curve_db()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    init_db()

'''
old way:

# Third-party
import numpy as np

valid_objtypes = ["bad", "marginal", "variable", "transient", ""]

dir = os.path.dirname(__file__)
data_path = os.path.abspath(os.path.join(dir, 'data/candidates/light_curves'))
db_filename = os.path.join(data_path, "lightcurves.db")

class CandidateLightCurveDB(object):
    
    def __init__(self, filename):
        if os.path.exists(filename):
            logging.info("Database file already exists")
            
        self.filename = filename
        self.conn = sqlite3.connect(self.filename)
        self.conn.row_factory = sqlite3.Row
    
    def create_table(self):
        c = self.conn.cursor()
        
        c.execute("""SELECT name FROM sqlite_master
                     WHERE type='table'
                     ORDER BY name""")
        
        if "light_curves" in [x[0] for x in c.fetchall()]:
            logging.warning("Table 'light_curves' already exists!")
            return
        
        c.execute("""CREATE TABLE light_curves
                 (source_id int, field_id int, ra real, dec real, looked_at int, obj_type text)""")
        
        self.conn.commit()
        c.close()
    
    def insert(self, source_id, field_id, ra, dec, looked_at=0, obj_type=""):
        c = self.conn.cursor()
        c.execute("INSERT INTO light_curves VALUES (?,?,?,?,?,?)", (source_id, field_id, ra, dec, looked_at, obj_type))
        self.conn.commit()
        c.close()
    
    def light_curve(self, source_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM light_curves WHERE source_id=?", (source_id,))
        results = c.fetchone()
        c.close()
        
        return results
    
    def update_obj_type(self, source_id, obj_type):
        if obj_type not in valid_objtypes:
            raise ValueError("obj_type can only be one of: [{}]".format(",".join(valid_objtypes)))
        
        c = self.conn.cursor()
        c.execute("UPDATE light_curves SET looked_at=1,obj_type=? WHERE source_id=?", (obj_type, source_id))
        self.conn.commit()
        c.close()
    
    def all_light_curves(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM light_curves")
        results = c.fetchall()
        desc = c.description
        c.close()
        
        #return dict([zip(desc,x) for x in results])
        return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Initialize database
    db = CandidateLightCurveDB(db_filename)
    db.create_table()
    
    pattr = re.compile("field(\d+)_id(\d+).npy")
    for lc_file in glob.glob(os.path.join(data_path, "*.npy")):
        field_id, source_id = map(int, pattr.search(lc_file).groups())
        
        if db.light_curve(source_id) == None:
            object_data = np.load(lc_file)
            ra = np.mean(object_data["alpha_j2000"])
            dec = np.mean(object_data["delta_j2000"])
            db.insert(source_id=source_id, field_id=field_id, ra=ra, dec=dec)
        else:
            logging.debug("Light curve {} already in database".format(source_id))
'''