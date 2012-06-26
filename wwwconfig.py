import os

_basedir = os.path.abspath(os.path.dirname(__file__))
ptf_basedir = "/home/adrian/projects/ptf"
LIGHT_CURVE_PATH = os.path.join(ptf_basedir, "data/candidates/light_curves/")

DEBUG = False

SECRET_KEY = 'testkey'
DATABASE_URI = "sqlite:///" + os.path.join(_basedir, "website.db")
DATABASE_CONNECT_OPTIONS = {}

LIGHT_CURVE_DATABASE_URI = "sqlite:///" + os.path.join(LIGHT_CURVE_PATH, "light_curves.db")
LIGHT_CURVE_DATABASE_CONNECT_OPTIONS = {}

ADMINS = []

del os