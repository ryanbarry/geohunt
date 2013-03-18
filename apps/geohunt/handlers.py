from tipfy import RequestHandler, Response, redirect, redirect_to, cached_property, render_json_response
from tipfy.ext.jinja2 import render_response
from tipfy.ext.session import SessionMixin, SessionMiddleware, FlashMixin
from tipfy.ext.wtforms import Form, fields, validators
from tipfy.ext.blobstore import BlobstoreUploadMixin
from google.appengine.api import urlfetch, blobstore, images
from google.appengine.ext.webapp import blobstore_handlers
from encode import multipart_encode, MultipartParam
import urllib
from models import *

import math
import random

# JSON error messages, since they're used so often
def MissingParams():
    return render_json_response({'status':{'code':99,'message':'Missing parameters'}})

def InvalidToken():
    return render_json_response({'status':{'code':98,'message':'Invalid Token'}})

def InvalidCid():
    return render_json_response({'status':{'code':97,'message':'Invalid CID'}})

def NoGameOn():
    return render_json_response({'status':{'code':20,'message':'No game in progress'}})


# push functionality
# second arg is message type: 0 = GAMEON, 1 = GAMEOVER, 2 = REPORT
def push(profile, msg, picurl = '', whofoundwhat = ''):
    if msg == 0:
        # GAMEON
        ckey = 'GAMEON'
        data = '{"push":{"type":"GAMEON"}}'
    elif msg == 1:
        # GAMEOVER
        ckey = 'GAMEOVER'
        data = '{"push":{"type":"GAMEOVER"}}'
    elif msg == 2:
        # REPORT
        ckey = 'REPORT'
        data = '{"push":{"type":"REPORT","content":{"event":"'+whofoundwhat+'","url":"'+picurl+'"}}}'
    else:
        return None
    
    # choose Android C2DM or Windows Push
    if profile.phonetype == 'android':
        authToken = 'DQAAAK0AAACmNeDRCNDBoeYozg2nsWLwmWDKlqpDz7jey0kqid61_3Qv48zK5JDKcoVsFqZ_7UAoaNI2gpcuX-CnALKrq-amws-RZL5Eb87kMjY_wXHyDYANfaedDVjW-oIIFX4Rxf472mbu0tiyhirng11nQ-NcF8qf5ZOFkCLUO0whsG9Pwyxo5Zbo9sChRKLDMDZKojETNWOFNfiCSt5S8x5CK72x-t8obSXzKIIowezBSvq7eQ'
        payload = {
            'registration_id':profile.registration_id,
            'collapse_key':ckey,
            'data':data
        }
        result = urlfetch.fetch(
            'https://android.clients.google.com/c2dm/send',
            payload = urllib.urlencode(payload),
            method = urlfetch.POST,
            headers = {'Authorization':'GoogleLogin auth='+authToken}
        )
    else:
        result = urlfetch.fetch(
            profile.registration_id, # this is the url for windows push
            payload = data,
            method = urlfetch.POST
        )
        
    return result


def pushReportAll(game, picurl, whofoundwhat):
    for profile in Profile.all().filter('game', game):
        push(profile, 2, picurl, whofoundwhat)


# main page stuff
class FrontPage(RequestHandler, SessionMixin, FlashMixin):
    middleware = [SessionMiddleware]
    
    def get(self):
        # get current game, be that the one in progress or the most recently created one
        game = Game.all().filter('is_on', True).get()
        if game is None:
            game = Game.all().order('-game_id').get()
        if game is None:
            game = Game(game_id=1, is_on=False)
            game.put()
        
        # get the profiles registered in the current game
        profiles = Profile.all().filter('game',game)
        return render_response('list_profiles.html', profiles = profiles, game_is_on=game.is_on, form=self.form, flash = self.get_flash())
    
    
    def post(self, **kwargs):
        if self.form.validate():
            rq_name = self.form.name.data
            rq_reg_id = self.form.reg_id.data
            rq_phonetype = self.form.phone_type.data
            # if there are no games yet, create one
            if Game.all().count() == 0:
                game = Game(game_id=1, is_on=False)
                game.put()
            else:
                # current game is either the one that is running, or the most recently created
                game = Game.all().filter('is_on', True).order('-game_id').get()
                if game is None:
                    game = Game.all().order('-game_id').get()
            
            if rq_name == None or rq_reg_id == None or rq_phonetype == None:
              self.set_flash('Profile was not registered because it was missing parameters. Name, registration_id, and phonetype are all required.')
            elif rq_phonetype != 'android' and rq_phonetype != 'windows':
              self.set_flash('Profile was not registered; phonetype must be android or windows.')
            else:
              if(Profile.all().filter('name',rq_name).get() != None):
                self.set_flash('Profile was not registered because supplied name is already used.')
              else:
                new_profile = Profile(
                  name = rq_name,
                  registration_id = rq_reg_id,
                  phonetype = rq_phonetype,
                  token = ''.join(random.choice('0123456789abcdef') for x in range(40)),
                  score = 0,
                  game = game)
                new_profile.put()  
                self.set_flash('Profile "' + rq_name + '" was successfully registered.')
#                if game.is_on:
#                    res = push(new_profile, 0)
#                    if res.status_code == 200:
#                        self.set_flash('Push message was successfully sent! (Game has already started)')
#                    else:
#                        self.set_flash('There was a problem sending you a push notification. (' +res.status_code+ ':' + res.content +')')
            return self.get(**kwargs)
        else:
            return self.get(**kwargs)
    
    @cached_property
    def form(self):
        return NewProfileForm(self.request)
    


class NewProfileForm(Form):
    csrf_protection = True
    name = fields.TextField('Name', validators=[validators.Required()])
    reg_id = fields.TextField('Reg ID', validators=[validators.Required()])
    phone_type = fields.SelectField('Phone Type', choices=[('android', 'Android'), ('windows', 'Windows')])


class TestPush(RequestHandler, SessionMixin, FlashMixin):
    middleware = [SessionMiddleware]
    
    def get(self):
        rq_token = self.request.args.get('token')
        rq_msgtype = self.request.args.get('msgtype')
        if rq_token is None or rq_msgtype is None:
            self.set_flash('Missing parameters for test push: token and msgtype (0=GAMEON,1=GAMEOVER,2=REPORT) must be set.')
        else:
            profile = Profile.all().filter('token', rq_token).get()
            if profile is None:
                self.set_flash('The token specified was not found.')
            else:
                if rq_msgtype == '0' or rq_msgtype == '1':
                    res = push(profile, int(rq_msgtype))
                    if res.status_code == 200:
                        self.set_flash('Test push (GAMEON/GAMEOVER) was successful!')
                    else:
                        self.set_flash('Test push failed. (' + str(res.status_code) + ' ' + res.content + ')')
                elif rq_msgtype == '2':
                    res = push(profile, 2, 'http://zef.me/wp-content/uploads/2008/02/funny-cat.jpg', 'This is a test REPORT push, the picture is funny.')
                    if res.status_code == 200:
                        self.set_flash('Test push (REPORT) was successful!')
                    else:
                        if profile.phonetype == 'android':
                            self.set_flash('Test push failed. (' + str(res.status_code) + ': ' + res.content + ')')
                        else:
                            self.set_flash('Test push failed. (' + str(res.status_code) + ')')
                else:
                    self.set_flash('Parameter msgtype must be 0 (GAMEON), 1 (GAMEOVER), or 2 (REPORT)')
        return redirect('/')


# here is the API that phones use
class Register(RequestHandler):
    def get(self):
        rq_name = self.request.args.get('name')
        rq_reg_id = self.request.args.get('registration_id')
        rq_phonetype = self.request.args.get('phonetype')
        if Game.all().count() == 0:
            Game(game_id=1, is_on=False).put()
            game = Game.all().get()
        elif Game.all().filter('is_on', True).count() == 0:
            game = Game.all().order('-game_id').get()
        else:
            game = Game.all().filter('is_on', True).order('-game_id').get()
        
        if rq_name is None or rq_reg_id is None or rq_phonetype is None:
            return MissingParams()
        elif rq_phonetype != 'android' and rq_phonetype != 'windows':
            return render_json_response({'status':{'code':99,'message':'Phonetype must be android or windows.'}})
        else:
            if not Profile.all().filter('name',rq_name).get() is None:
                return render_json_response({'status':{'code':99,'message':'Supplied name is not unique.'}})
            elif not Profile.all().filter('registration_id',rq_reg_id).get() is None:
                return render_json_response({'status':{'code':99,'message':'Supplied registration id is not unique.'}})
            else:
                new_profile = Profile(
                    name = rq_name,
                    registration_id = rq_reg_id,
                    phonetype = rq_phonetype,
                    token = ''.join(random.choice('0123456789abcdef') for x in range(40)),
                    score = 0,
                    game = game
                )
                new_profile.put()
#                if game.is_on:
#                    push(new_profile, 0)
                return render_json_response({'response':{'token':new_profile.token},'status':{'code':0,'message':'Success'}})
    


class ReRegister(RequestHandler):
    def get(self):
        rq_reg_id = self.request.args.get('registration_id')
        rq_token = self.request.args.get('token')
        
        if rq_reg_id is None or rq_token is None:
            return MissingParams()
        elif not Profile.all().filter('registration_id',rq_reg_id).get() is None:
            return render_json_response({'status':{'code':90,'message':'Supplied registration id is not unique.'}})
        else:
            profile = Profile.all().filter('token',rq_token).get()
            if profile is None:
                return InvalidToken()
            else:
                profile.registration_id = rq_reg_id
                profile.put()
                return render_json_response({'response':{'token':profile.token},'status':{'code':0,'message':'success'}})


class GetN(RequestHandler):
    def get(self):
        rq_token = self.request.args.get('token')
        if rq_token is None:
            return MissingParams()
        else:
            prof = Profile.all().filter('token', rq_token).get()
            if prof is None:
                return InvalidToken()
            elif not prof.game.is_on:
                return NoGameOn()
            else:
                num_points = CheckinPoint.all().filter('game', prof.game).count()
                return render_json_response({'response':{'n':str(num_points)},'status':{'code':0,'message':'Success'}})


class Query(RequestHandler):
    def get(self):
        rq_cid = self.request.args.get('cid')
        rq_token = self.request.args.get('token')
        rq_lat = self.request.args.get('latitude')
        rq_lon = self.request.args.get('longitude')
        
        if rq_cid is None or rq_token is None or rq_lat is None or rq_lon is None:
            return MissingParams()
        else:
            profile = Profile.all().filter('token', rq_token).get()
            if profile is None:
                return InvalidToken()
            else:
                game = profile.game
                if not game.is_on:
                    return NoGameOn()
                else:
                    point = CheckinPoint.all().filter('game', game).filter('cid', int(rq_cid)).get()
                    if point is None:
                        return InvalidCid()
                    else:
                        dist = math.sqrt((float(rq_lat) - point.latitude)*(float(rq_lat)- point.latitude) + (float(rq_lon) - point.longitude)*(float(rq_lon) - point.longitude))
                        angle = math.atan2(point.longitude - float(rq_lon), point.latitude - float(rq_lat))
                        return render_json_response({'response':{'distance':dist, 'angle':angle}, 'status':{'code':0,'message':'Success'}})


class CheckinHandler(RequestHandler):
    def get(self):
        rq_cid = self.request.args.get('cid')
        rq_token = self.request.args.get('token')
        rq_lat = self.request.args.get('latitude')
        rq_lon = self.request.args.get('longitude')
        
        if rq_cid is None or rq_token is None or rq_lat is None or rq_lon is None:
            return MissingParams()
        else:
            profile = Profile.all().filter('token', rq_token).get()
            if profile is None:
                return InvalidToken()
            else:
                if not profile.game.is_on:
                    return NoGameOn()
                else:
                    point = CheckinPoint.all().filter('game', profile.game).filter('cid', int(rq_cid)).get()
                    if point is None:
                        return InvalidCid()
                    else:
                        if not Checkin.all().filter('profile', profile).filter('point', point).get() is None:
                            return render_json_response({'status':{'code':13,'message':'Already checked in here.'}})
                        elif not Checkin.all().filter('profile', profile).filter('achieved', False).get() is None:
                            return render_json_response({'status':{'code':12,'message':'Currently locked in at another location.'}})
                        else:
                            dist = math.sqrt((float(rq_lat) - point.latitude)*(float(rq_lat)- point.latitude) + (float(rq_lon) - point.longitude)*(float(rq_lon) - point.longitude))
                            if dist > point.hint_dist:
                                return render_json_response({'status':{'code':10,'message':'Too far from checkin point.'}})
                            else:
                                if Checkin.all().count() == 0:
                                    cid = 1
                                else:
                                    cid = Checkin.all().order('-cid').get().cid + 1
                                checkin = Checkin(profile = profile, point = point, achieved = False, cid = cid)
                                checkin.put()
                                return render_json_response({'response':{'hint':point.hint}, 'status':{'code':0,'message':'Success'}})


class CancelCheckin(RequestHandler):
    def get(self):
#        rq_cid = self.request.args.get('cid')
        rq_token = self.request.args.get('token')
        
        if rq_token is None:
            return MissingParams()
        else:
            profile = Profile.all().filter('token', rq_token).get()
            if profile is None:
                return InvalidToken()
            else:
                if not profile.game.is_on:
                    return NoGameOn()
                else:
                    ckin = Checkin.all().filter('profile', profile).filter('achieved', False).get()
                    if ckin is None:
                        return render_json_response({'status':{'code':11,'message':'Not locked in to any location.'}})
                    else:
                        ckin.delete()
                        return render_json_response({'response':{'message':'You are no longer locked to a checkin.'},'status':{'code':0,'message':'Success'}})


class UploadImage(RequestHandler):
    def post(self):
        rq_cid = self.request.form.get('cid')
        rq_token = self.request.form.get('token')
        rq_image = self.request.files.get('image')
        
        if rq_token is None or rq_cid is None:
            return MissingParams()
        else:
            profile = Profile.all().filter('token', rq_token).get()
            if profile is None:
                return InvalidToken()
            elif not profile.game.is_on:
                return NoGameOn()
            else:
                point = CheckinPoint.all().filter('cid', int(rq_cid)).get()
                if point is None:
                    return InvalidCid()
                else:
                    ckin = Checkin.all().filter('profile', profile)
                    if ckin.filter('achieved', False).count() == 0:
                        return render_json_response({'status':{'code':13,'message':'You have no unachieved checkins.'}})
                    else:
                        ckin = ckin.filter('point', point).get()
                        if ckin is None:
                            return render_json_response({'status':{'code':11,'message':'You are checked in at another location!'}})
                        else:
                            rq_image.seek(0,2)
                            img_content_length = rq_image.tell()
                            rq_image.seek(0,0)
                            if img_content_length == 0:
                                return render_json_response({'status':{'code':95,'message':'You have not included a picture!'}})
                            else:
                                params = []
                                params.append(
                                    MultipartParam(
                                        "file",
                                        filename=ckin.cid,
                                        value=rq_image.read()
                                    )
                                )
                                payloadgen, headers = multipart_encode(params)
                                payload = str().join(payloadgen)
                                url = blobstore.create_upload_url('/handle_upload')
                                try:
                                    result = urlfetch.fetch(
                                        url=url,
                                        payload=payload,
                                        method=urlfetch.POST,
                                        headers=headers,
                                        deadline=10,
                                        follow_redirects=False
                                    )
                                    return render_json_response({'status':{'code':0,'message':'Success'}})
                                except:
                                    return render_json_response({'status':{'code':81,'message':'There was a server error uploading the image.'}})


class UploadHandler(RequestHandler, BlobstoreUploadMixin):
    def post(self):
      upload_files = self.get_uploads('file')
      blob_info = upload_files[0]
      
      ckin = Checkin.all().filter('cid', int(blob_info.filename)).get()
      ckin.achieved = True
      ckin.picture = db.Link(images.get_serving_url(blob_info.key()))
      ckin.put()
      
      profile = ckin.profile
      profile.score = profile.score + 1;
      profile.put()
      pushReportAll(profile.game, ckin.picture, profile.name + ' found checkin point ' + str(ckin.cid))
      
      self.redirect('/')


# administration interface handlers
class AdminMain(RequestHandler, SessionMixin, FlashMixin):
    middleware = [SessionMiddleware]
    def get(self):
        return render_response('admin_main.html', flash=self.get_flash(), games = Game.all(), points = CheckinPoint.all(), profiles = Profile.all())


class AdminGame(RequestHandler, SessionMixin, FlashMixin):
    middleware = [SessionMiddleware]
    def get(self, gid):
        game = Game.all().filter('game_id', gid).get()
        if game is None:
            return Response('No game with that id was found')
        else:
            return render_response('admin_game.html', flash = self.get_flash(), form=self.form, game = game, profiles = Profile.all().filter('game',game), points = CheckinPoint.all().filter('game',game))
    
    def post(self, gid):
        if self.form.validate():
            rq_hint = self.form.hint.data
            rq_hint_dist = float(self.form.hint_dist.data)
            rq_longitude = float(self.form.longitude.data)
            rq_latitude = float(self.form.latitude.data)
            
            if rq_hint is None or rq_hint_dist is None or rq_longitude is None or rq_latitude is None:
                self.set_flash('Checkin point was not created because some or all of the parameters were missing. All are required.')
            elif rq_hint_dist < 0:
                self.set_flash('Checkin point not created: hint distance must be positive!')
            elif rq_longitude < -180 or rq_longitude > 180:
                self.set_flash('Checkin point not created: longitude must be in the range [-180, 180]')
            elif rq_latitude < -90 or rq_latitude > 90:
                self.set_flash('Checkin point not created: latitude must be in the range [-90, 90]')
            else:
                game = Game.all().filter('game_id', gid).get()
                last_point = CheckinPoint.all().filter('game',game).order('-cid').get()
                if last_point is None:
                    point_id = 1
                else:
                    point_id = last_point.cid + 1
                new_point = CheckinPoint(cid = point_id, hint = rq_hint, hint_dist = rq_hint_dist, latitude = rq_latitude, longitude = rq_longitude, game = game)
                new_point.put()
                self.set_flash('Checkin point successfully created!')
            
        return self.get(gid)
            
    @cached_property
    def form(self):
       return NewCheckinPointForm(self.request)


class NewCheckinPointForm(Form):
   csrf_protection = True
   hint = fields.TextField('Hint', validators=[validators.Required()])
   hint_dist = fields.DecimalField('Hint Distance', default=0.0002, places=5, validators=[validators.Required(),validators.NumberRange(min=0)])
   latitude = fields.DecimalField('Latitude', validators=[validators.Required(),validators.NumberRange(min=-90,max=90)])
   longitude= fields.DecimalField('Longitude', validators=[validators.Required(),validators.NumberRange(min=-180,max=180)])


class AdminNewGame(RequestHandler, SessionMixin, FlashMixin):
    middleware = [SessionMiddleware]
    def get(self):
        if not Game.all().filter('is_on', True).get() is None:
            self.set_flash('There is already a game in progress. End the current game before creating a new one.')
        else:
            game = Game.all().order('-game_id').get()
            if game is None:
                new_game = Game(game_id=1, is_on=False)
            else:
                new_game = Game(game_id=game.game_id+1, is_on=False)
            new_game.put()
            self.set_flash('Game created successfully!')
        return redirect('/admin')


class GameOn(RequestHandler, SessionMixin, FlashMixin):
    middleware = [SessionMiddleware]
    def get(self, gid):
        game = Game.all().filter('game_id', gid).get()
        if game is None:
            return Response('No game with that id was found')
        else:
            game.is_on = True
            game.put()
            for profile in Profile.all().filter('game',game):
                response = push(profile, 0)
                if response.status_code != 200:
                    self.set_flash('Unable to push to player named "' + profile.name + '". Response from push server: '+str(response.status_code)+': '+response.content)
            self.set_flash('Game was started!')
            return redirect_to('admin-game', gid = game.game_id)


class GameOver(RequestHandler, SessionMixin, FlashMixin):
    middleware = [SessionMiddleware]
    def get(self, gid):
        game = Game.all().filter('game_id', gid).get()
        if game is None:
            return Response('No game with that id was found')
        else:
            for profile in Profile.all().filter('game',game):
                response = push(profile, 1)
                if response.status_code != 200:
                    self.set_flash('Unable to push to player named "' + profile.name + '". Response from push server: '+response.status_code+': '+response.content)
            self.set_flash('Game was ended!')
            game.is_on = False
            game.put()
            return redirect_to('admin-game', gid = game.game_id)


