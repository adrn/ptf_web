import os

BASEDIR = _basedir = os.path.abspath(os.path.dirname(__file__))
ptf_basedir = "/home/adrian/projects/ptf"
LIGHT_CURVE_PATH = os.path.join(ptf_basedir, "data/candidates/light_curves/")

DEBUG = False
SERVER_NAME = "deimos.astro.columbia.edu:5000"
SESSION_COOKIE_NAME = "deimos"

SECRET_KEY = '/3yXR~XHA0Zr98jLWX/,?RTH!jmN]'
DATABASE_URI = "sqlite:///" + os.path.join(_basedir, "website.db")
DATABASE_CONNECT_OPTIONS = {}

LIGHT_CURVE_DATABASE_URI = "sqlite:///" + os.path.join(LIGHT_CURVE_PATH, "light_curves.db")
LIGHT_CURVE_DATABASE_CONNECT_OPTIONS = {}

IPAC_DATA_URL = "http://kanaloa.ipac.caltech.edu/ibe/data/ptf/dev/process"
IPAC_SEARCH_URL = "http://kanaloa.ipac.caltech.edu/ibe/search/ptf/dev/process"

ADMINS = []

del os