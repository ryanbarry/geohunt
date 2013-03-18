from google.appengine.ext import db

# datastore models

# represents a single game
class Game(db.Model):
    game_id = db.IntegerProperty(required=True,indexed=True)
    is_on = db.BooleanProperty(required=True)


# each profile represents a phone registration
class Profile(db.Model):
    name = db.StringProperty(required=True)
    registration_id = db.StringProperty(required=True,indexed=True)
    token = db.StringProperty(required=True,indexed=True)
    phonetype = db.StringProperty(required=True,choices=['android','windows'])
    score = db.IntegerProperty(required=True)
    game = db.ReferenceProperty(Game, required=True)


# the points that users will be checking into during the game
class CheckinPoint(db.Model):
    cid = db.IntegerProperty(required=True,indexed=True)
    latitude = db.FloatProperty(required=True)
    longitude = db.FloatProperty(required=True)
    hint = db.StringProperty(required=True)
    hint_dist = db.FloatProperty(required=True)
    game = db.ReferenceProperty(Game, required=True)


# represents a single checkin for a single user at a single checkin point
class Checkin(db.Model):
    cid = db.IntegerProperty(required=True,indexed=True)
    profile = db.ReferenceProperty(Profile,required=True,indexed=True)
    point = db.ReferenceProperty(CheckinPoint,required=True,indexed=True)
    achieved = db.BooleanProperty(required=True,indexed=True)
    time = db.DateTimeProperty(auto_now=True)
    picture = db.LinkProperty()

