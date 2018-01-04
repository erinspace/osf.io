# -*- coding: utf-8 -*-
'''Consolidates settings from defaults.py and local.py.

::
    >>> from api.base import settings
    >>> settings.API_BASE
    'v2/'
'''
import os
from urlparse import urlparse
import warnings
import itertools

from .defaults import *  # noqa

try:
    from .local import *  # noqa
except ImportError as error:
    warnings.warn('No api/base/settings/local.py settings file found. Did you remember to '
                  'copy local-dist.py to local.py?', ImportWarning)

settings_to_check = ('WATERBUTLER_JWE_SECRET', 'WATERBUTLER_JWE_SALT', 'WATERBUTLER_JWT_SECRET', 'JWT_SECRET', 'JWE_SECRET',
                     'DEFAULT_HMAC_SECRET', 'POPULAR_LINKS_NODE', 'NEW_AND_NOTEWORTHY_LINKS_NODE', 'SENSITIVE_DATA_SALT',
                     'SENSITIVE_DATA_SECRET', 'BYPASS_THROTTLE_TOKEN')


if not DEV_MODE and os.environ.get('DJANGO_SETTINGS_MODULE') == 'api.base.settings':
    from . import local
    from . import defaults
    for setting in settings_to_check:
        assert getattr(local, setting, None) and getattr(local, setting, None) != getattr(defaults, setting, None), '{} must be specified in local.py when DEV_MODE is False'.format(setting)

def load_origins_whitelist():
    global ORIGINS_WHITELIST
    from osf.models import Institution, PreprintProvider

    institution_origins = tuple(domain.lower() for domain in itertools.chain(*Institution.objects.values_list('domains', flat=True)))

    preprintprovider_origins = tuple(preprintprovider.domain.lower() for preprintprovider in PreprintProvider.objects.exclude(domain=''))

    ORIGINS_WHITELIST = tuple(urlparse(url).geturl().lower().split('{}://'.format(urlparse(url).scheme))[-1] for url in institution_origins + preprintprovider_origins)

def build_latest_versions(version_data):
    """Builds a dict with greatest version keyed for each major version"""
    ret = {}
    for version in reversed(version_data):
        major_version = int(version.split('.')[0])
        if major_version not in ret:
            ret[major_version] = version
    return ret

LATEST_VERSIONS = build_latest_versions(REST_FRAMEWORK['ALLOWED_VERSIONS'])
