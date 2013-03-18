from tipfy import Rule

def get_rules(app):
  rules = [
    Rule('/', endpoint='main', handler='apps.geohunt.handlers.FrontPage'),
    Rule('/test_push', endpoint='test-push', handler='apps.geohunt.handlers.TestPush'),
    Rule('/register', endpoint='json-register', handler='apps.geohunt.handlers.Register'),
    Rule('/update_reg_id', endpoint='json-reregister', handler='apps.geohunt.handlers.ReRegister'),
    Rule('/get_n', endpoint='json-get-n', handler='apps.geohunt.handlers.GetN'),
    Rule('/query', endpoint='json-query', handler='apps.geohunt.handlers.Query'),
    Rule('/checkin', endpoint='json-checkin', handler='apps.geohunt.handlers.CheckinHandler'),
    Rule('/cancel_checkin', endpoint='json-cancel-checkin', handler='apps.geohunt.handlers.CancelCheckin'),
    Rule('/upload', endpoint='json-upload', handler='apps.geohunt.handlers.UploadImage'),
    Rule('/handle_upload', endpoint='blob-handle-uplaod', handler='apps.geohunt.handlers.UploadHandler'),
    Rule('/admin/', endpoint='admin-main', handler='apps.geohunt.handlers.AdminMain'),
    Rule('/admin/newgame', endpoint='admin-main', handler='apps.geohunt.handlers.AdminNewGame'),
    Rule('/admin/game/<int:gid>', endpoint='admin-game', handler='apps.geohunt.handlers.AdminGame'),
    Rule('/admin/game/<int:gid>/start', endpoint='admin-start-game', handler='apps.geohunt.handlers.GameOn'),
    Rule('/admin/game/<int:gid>/stop', endpoint='admin-stop-game', handler='apps.geohunt.handlers.GameOver'),
  ]
  return rules