# Standard library
import os
import json
import re
import datetime
import urllib

from flask import Blueprint, render_template, session, redirect, url_for, \
     request, flash, g, jsonify, abort, send_file
from flaskext.openid import COMMON_PROVIDERS

import numpy as np
import pyfits as pf
import pymongo
from bson.objectid import ObjectId
from werkzeug import Response

from ptf.db.mongodb import update_light_curve_document_tags

from ptf_web import oid, app
from ptf_web.utils import requires_login, request_wants_json
from ptf_web.database import db_session, User, light_curve_collection, field_collection, table_state_collection

mod = Blueprint('data', __name__)

# Jsonify to deal with mongodb objectid
class MongoJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, ObjectId):
            return unicode(obj)
        return json.JSONEncoder.default(self, obj)

def jsonify(*args, **kwargs):
    """ jsonify with support for MongoDB ObjectID """
    return Response(json.dumps(dict(*args, **kwargs), cls=MongoJsonEncoder), mimetype='application/json')

def str_encode_field_ccd_source(field_id, ccd_id, source_id):
    return "f{}c{}s{}".format(field_id, ccd_id, source_id)

def str_decode_field_ccd_source(string):
    pattr = re.compile("f([0-9]+)c([0-9]+)s([0-9]+)")
    return map(int, pattr.search(string).groups())

@mod.route('/tagged/<tag_name>', methods=["GET"])
@requires_login
def tagged(tag_name):
    """ """
    if tag_name == "none":
        tag_name = []

    print "IN HERE!!"

    # Default is to get Field ID, CCD ID, Source ID
    mongo_fields = request.args.get("fields", ["field_id", "ccd_id", "source_id", "indices", "ra", "dec", "microlensing_fit", "tags", "viewed"])
    sort = [("field_id",pymongo.ASCENDING), ("ccd_id",pymongo.ASCENDING), ("source_id",pymongo.ASCENDING)]
    light_curves = light_curve_collection.find({"tags" : tag_name}, fields=mongo_fields, sort=sort)

    retrieved = []
    for lc in light_curves:
        if not lc.has_key("viewed"):
            lc["viewed"] = False
        retrieved.append(dict(lc))

    return jsonify(aaData=retrieved)

@mod.route('/field/<field_id>', methods=["GET"])
@requires_login
def field(field_id):
    """ """
    if field_id == "none":
        return jsonify(aaData=[])

    # Default is to get Field ID, CCD ID, Source ID
    mongo_fields = request.args.get("fields", ["field_id", "ccd_id", "source_id", "indices", "ra", "dec", "microlensing_fit", "tags", "viewed"])
    sort = [("field_id",pymongo.ASCENDING), ("ccd_id",pymongo.ASCENDING), ("source_id",pymongo.ASCENDING)]
    light_curves = light_curve_collection.find({"field_id" : int(field_id)}, fields=mongo_fields, sort=sort)

    retrieved = []
    for lc in light_curves:
        if not lc.has_key("viewed"):
            lc["viewed"] = False
        retrieved.append(dict(lc))

    return jsonify(aaData=retrieved)

@mod.route('/json/candidate_list', methods=["GET"])
@requires_login
def candidate_list():
    """ Load candidate light curves from MongoDB """

    search = {}

    # Default is to sort by CCD, Source ID
    if request.args.has_key("field_id"):
        field_ids = [int(x) for x in request.args.getlist("field_id")]
        search["field_id"] = {"$in" : field_ids}

    #search["indices"] = {"delta_chi_squared" : {"$gt" : 500}}
    #search["field_id"] = {"$in" : [4465]} # HACK

    # Default is to return all, e.g. num=0
    num = request.args.get("num", 0)

    # Default is to sort by CCD, Source ID
    if request.args.has_key("sort"):
        sort = [(x,pymongo.ASCENDING) for x in request.args.getlist("sort")]
    else:
        sort = [("field_id",pymongo.ASCENDING), ("ccd_id",pymongo.ASCENDING), ("source_id",pymongo.ASCENDING)]

    # Default is to get Field ID, CCD ID, Source ID
    mongo_fields = request.args.get("fields", ["field_id", "ccd_id", "source_id", "indices", "ra", "dec", "microlensing_fit", "tags", "viewed"])

    raw_candidates = light_curve_collection.find(search, fields=mongo_fields, sort=sort, limit=int(num))
    for cand in raw_candidates:
        if not cand.has_key("viewed"):
            cand["viewed"] = False

    candidates = []
    for c in list(raw_candidates):
        candidates.append(dict(c))

    return jsonify(aaData=list(candidates))

@mod.route('/json/candidate_data', methods=["GET"])
@requires_login
def candidate_data():
    """ Load candidate light curves from MongoDB """

    search = {}
    search["field_id"] = int(request.args["field_id"])
    search["ccd_id"] = int(request.args["ccd_id"])
    search["source_id"] = int(request.args["source_id"])

    candidate = light_curve_collection.find_one(search)
    return jsonify(light_curve=candidate)

@mod.route('/json/fieldlist', methods=["GET"])
@requires_login
def field_list():
    field_ids = light_curve_collection.distinct("field_id")
    fields = []
    for field_id in sorted(field_ids):
        field_document = field_collection.find_one({"_id" : int(field_id)})
        field_data = dict()
        field_data["field_id"] = field_id
        field_data["num_rband"] = len(field_document["exposures"][field_document["exposures"].keys()[0]]["mjd"])

        vieweds = list(light_curve_collection.find({"field_id" : int(field_id)}, fields=["viewed"]))
        vieweds = np.array([lcd["viewed"] if lcd.has_key("viewed") else False for lcd in vieweds])

        field_data["num_viewed"] = str(sum(vieweds))
        field_data["num_total"] = str(len(vieweds))
        fields.append(field_data)

    return jsonify(aaData=fields)

@mod.route('/data', methods=["GET"])
@requires_login
def index():
    all_tags = []
    for tag in sorted(light_curve_collection.distinct("tags")):
        all_tags.append((urllib.quote(tag), " ".join([word.capitalize() for word in tag.split()])))

    return render_template('data/index.html', all_tags=all_tags)

@mod.route('/data/table/tag/<tag_name>', methods=["GET"])
@requires_login
def table_tag(tag_name):
    tag = str(tag_name)

    #return render_template('data/table.html', tags="&".join([urllib.quote(tag) for tag in tags]))
    return render_template('data/table.html', tag=urllib.quote(tag))

@mod.route('/data/table/field/<field_id>', methods=["GET"])
@requires_login
def table_field(field_id):
    field_id = int(field_id)
    field_document = field_collection.find_one({"_id" : field_id})
    return render_template('data/table.html', field_id=field_id, was_inspected=field_document["inspected"])

# Redirect requests from the form on data/index.html
@mod.route('/data/table/field', methods=["GET"])
@requires_login
def table_field_redirect():
    field_id = request.args.get("id", None)

    if field_id == None:
        abort(404)

    return redirect("/data/table/field/{}".format(field_id))

@mod.route('/candidates/plot', methods=["GET"])
@requires_login
def plot():
    if not request.args.has_key("source_id") or not request.args.has_key("field_id") or not request.args.has_key("ccd_id"):
        abort(404)

    source_id = int(request.args["source_id"])
    field_id = int(request.args["field_id"])
    ccd_id = int(request.args["ccd_id"])

    if request.args.has_key("set_tags"):
        if request.args["set_tags"] == "true":
            try:
                tags = [str(x) for x in request.args.getlist("tags")]
            except KeyError:
                tags = []

            if request.args.has_key("new_tag"):
                tags.append(str(request.args["new_tag"]))

            lc_document = light_curve_collection.find_one({"field_id" : field_id, "ccd_id" : ccd_id, "source_id" : source_id})

            tags = [str(tag).strip() for tag in tags if len(tag.strip()) > 0]

            if "galaxy" in tags or "qso" in tags or "bad data" in tags:
                if "variable star" in tags:
                    tags.pop(tags.index("variable star"))

            if "bad data" in tags or "not interesting" in tags:
                if "candidate" in tags:
                    tags.pop(tags.index("candidate"))

            if lc_document != None:
                update_light_curve_document_tags(lc_document, tags, light_curve_collection)

    lc_document = light_curve_collection.find_one({"field_id" : field_id, "ccd_id" : ccd_id, "source_id" : source_id})
    if not lc_document.has_key("viewed") or not lc_document["viewed"]:
        first_view = True
        light_curve_collection.update({"field_id" : field_id, "ccd_id" : ccd_id, "source_id" : source_id}, {"$set" : {"viewed" : True}})
    else:
        first_view = False

    return render_template('data/plot.html', light_curve=lc_document, all_tags=sorted(light_curve_collection.distinct("tags")), first_view=first_view)

@mod.route('/mongo/update_field_inspected', methods=["POST"])
@requires_login
def update_field_inspected():
    """ Update whether the given field id has been inspected """

    if not request.form.has_key("field_id"):
        abort(404)

    field_id = int(request.form["field_id"])

    if request.form.has_key("inspected"):
        was_inspected = bool(int(request.form["inspected"]))
    else:
        was_inspected = False

    field_collection.update({"_id" : field_id}, {"$set" : {"inspected" : was_inspected}})

    return ""

@mod.route('/mongo/save_table_state', methods=["POST"])
@requires_login
def save_table_state():
    """ Save the current state of the table for next / previous buttons """

    user_id = g.user.id

    json_data = request.json

    table_state_list = []
    for ii in range(len(json_data["field_id"])):
        field_id = json_data["field_id"][ii]
        ccd_id = json_data["ccd_id"][ii]
        source_id = json_data["source_id"][ii]

        table_state_list.append(str_encode_field_ccd_source(field_id, ccd_id, source_id))

    # See if there is currently a state stored for this user
    table_state = table_state_collection.find_one({"user_id" : user_id})

    if table_state == None:
        table_state = dict()
        table_state["user_id"] = user_id
        table_state["state"] = table_state_list
        table_state_collection.insert(table_state, safe=True)
    else:
        table_state_collection.update({"user_id" : user_id}, {"$set" : {"state" : table_state_list}})

    return ""

@mod.route('/mongo/previous_next_light_curve', methods=["GET"])
@requires_login
def previous_next_light_curve():
    """ Load the current state of the table for next / previous buttons """

    if not request.args.has_key("source_id") or not request.args.has_key("field_id") or not request.args.has_key("ccd_id"):
        abort(404)

    field_id = int(request.args["field_id"])
    ccd_id = int(request.args["ccd_id"])
    source_id = int(request.args["source_id"])

    user_id = g.user.id
    table_state = table_state_collection.find_one({"user_id" : user_id})

    if table_state == None:
        return jsonify({})
    else:
        idx = table_state["state"].index(str_encode_field_ccd_source(field_id, ccd_id, source_id))
        if idx > len(table_state["state"])-1:
            next_idx = -1
        else:
            next_idx = idx+1

        return jsonify(previous=str_decode_field_ccd_source(table_state["state"][idx-1]),
                       next=str_decode_field_ccd_source(table_state["state"][next_idx]))
