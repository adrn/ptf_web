from flask import Blueprint, render_template, session, redirect, url_for, \
     request, flash, g, jsonify, abort
from flaskext.openid import COMMON_PROVIDERS

import numpy as np
import sqlalchemy

from ptf_web import oid
from ptf_web.utils import requires_login, request_wants_json
from ptf_web.database import db_session, User, lc_db_session, LightCurve

mod = Blueprint('candidates', __name__)

def get_candidates(sort_key, reverse):
    candidates = []
    for light_curve in lc_db_session.query(LightCurve).all():
         candidates.append(light_curve.to_json())
    
    try:
        candidates = sorted(candidates, key=lambda x: x[sort_key], reverse=reverse)
    except KeyError:
        flash(u"Invalid table sort key.")
    
    return candidates

def get_key(key, sort_key, reverse):
    vals = []
    
    if key == sort_key:
        for light_curve in lc_db_session.query(LightCurve).all():
             vals.append({key : getattr(light_curve, key)})
    else:
        for light_curve in lc_db_session.query(LightCurve).all():
             vals.append({key : getattr(light_curve, key), sort_key : getattr(light_curve, sort_key)})
    
    vals = [x[key] for x in sorted(vals, key=lambda x: x[sort_key], reverse=reverse)]
    
    return vals

@mod.route('/candidates', methods=["GET"])
@requires_login
def index():
    
    try:
        sort_key = request.args["sort_key"]
    except KeyError:
        sort_key = "matchedSourceID"
    
    try:
        rev = request.args["reverse"]
        reverse = True
    except KeyError:
        reverse = False
    
    candidates = get_candidates(sort_key, reverse)
    
    session["sort_key"] = sort_key
    session["reverse"] = reverse
    session.modified = True
    
    return render_template('candidates/index.html', candidates=candidates)

@mod.route('/candidates/plot', methods=["GET"])
@requires_login
def plot():
    if not request.args.has_key("matchedSourceID"):
        abort(404)
    
    try:
        source_id = int(request.args["matchedSourceID"])
    except:
        light_curve = None
        flash(u"Invalid Source ID")
    
    try:
        light_curve = lc_db_session.query(LightCurve).filter(LightCurve.matchedSourceID == int(request.args["matchedSourceID"])).one()
    except sqlalchemy.orm.exc.NoResultFound:
        light_curve = None
        flash(u"Source ID not in database.")
    
    if session.has_key("sort_key"):
        sort_key = session["sort_key"]
    else:
        sort_key = "matchedSourceID"
    
    if session.has_key("reverse"):
        reverse = session["reverse"]
    else:
        reverse = False
        
    source_ids = get_key("matchedSourceID", sort_key, reverse)
    this_index = source_ids.index(source_id)
    
    if this_index == 0:
        previous_id = None
    else:
        previous_id = source_ids[this_index-1]
        
    if this_index == len(source_ids)-1:
        next_id = None
    else:
        next_id = source_ids[this_index+1]
    
    return render_template('candidates/plot.html', light_curve=light_curve, previous_id=previous_id, next_id=next_id)

@mod.route('/candidates/data', methods=["GET"])
@requires_login
def data():
    if not request.args.has_key("matchedSourceID"):
        abort(404)
        
    try:
        source_id = int(request.args["matchedSourceID"])
    except:
        light_curve = None
        flash(u"Invalid Source ID")
    
    try:
        light_curve = lc_db_session.query(LightCurve).filter(LightCurve.matchedSourceID == int(request.args["matchedSourceID"])).one()
    except sqlalchemy.orm.exc.NoResultFound:
        light_curve = None
        flash(u"Source ID not in database.")
    
    lc_dict = light_curve.to_json()
    lc_data = light_curve.data
    lc_dict["mjd"] = list(lc_data["mjd"].astype(float))
    lc_dict["mag"] = list(lc_data["mag"].astype(float))
    lc_dict["error"] = list(lc_data["error"].astype(float))
    
    return jsonify(light_curve=lc_dict)

@mod.route('/candidates/ptfImage', methods=["GET"])
@requires_login
def ptfImage():
    if not request.args.has_key("matchedSourceID"):
        abort(404)
    
    # TODO: Read in PTF credentials from ptf_credentials
    
    # TODO: Image stuff..
