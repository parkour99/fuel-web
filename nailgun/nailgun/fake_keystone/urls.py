# -*- coding: utf-8 -*-

#    Copyright 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import web

from nailgun.fake_keystone.handlers import EndpointsHandler
from nailgun.fake_keystone.handlers import ServicesHandler
from nailgun.fake_keystone.handlers import TokensHandler
from nailgun.fake_keystone.handlers import VersionHandler

urls = (
    r"/v2.0/?$", VersionHandler.__name__,
    r"/v2.0/tokens/?$", TokensHandler.__name__,
    r"/v2.0/OS-KSADM/services/?$", ServicesHandler.__name__,
    r"/v2.0/endpoints/?$", EndpointsHandler.__name__,
)

_locals = locals()


def app():
    return web.application(urls, _locals)
