# -*- coding: utf-8 -*-
"""
    config
    ~~~~~~

    Configuration settings.

    :copyright: 2009 by tipfy.org.
    :license: BSD, see LICENSE for more details.
"""
config = {}

# Configurations for the 'tipfy' module.
config['tipfy'] = {
    # Enable debugger. It will be loaded only in development.
    'middleware': [
        'tipfy.ext.debugger.DebuggerMiddleware',
    ],
    # Enable the Hello, World! app example.
    'apps_installed': [
        'apps.geohunt',
    ],
}

config['tipfy.ext.session'] = {
    'secret_key' : 'laH42JKLfjHHLFKJ8932jJKJ23',
    'cookie_name': 'cs176b-geohunt-tipfy'
}
