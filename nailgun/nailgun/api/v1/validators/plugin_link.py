# -*- coding: utf-8 -*-
#    Copyright 2015 Mirantis, Inc.
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

from nailgun.api.v1.validators.base import BasicValidator
from nailgun.api.v1.validators.json_schema import plugin_link
from nailgun import errors
from nailgun import objects


class PluginLinkValidator(BasicValidator):
    collection_schema = plugin_link.PLUGIN_LINKS_SCHEMA

    @classmethod
    def validate(cls, data):
        parsed = super(PluginLinkValidator, cls).validate(data)
        cls.validate_schema(
            parsed,
            plugin_link.PLUGIN_LINK_SCHEMA
        )
        if objects.PluginLinkCollection.filter_by(
            None,
            url=parsed['url']
        ).first():
            raise errors.AlreadyExists(
                "Plugin link with URL {0} already exists".format(
                    parsed['url']),
                log_message=True)
        return parsed

    @classmethod
    def validate_update(cls, data, instance):
        parsed = super(PluginLinkValidator, cls).validate(data)
        cls.validate_schema(parsed, plugin_link.PLUGIN_LINK_UPDATE_SCHEMA)
        if objects.PluginLinkCollection.filter_by_not(
            objects.PluginLinkCollection.filter_by(
                None,
                url=parsed.get('url', instance.url)
            ),
            id=instance.id
        ).first():
            raise errors.AlreadyExists(
                "Plugin link with URL {0} already exists".format(
                    parsed['url']),
                log_message=True)
        return parsed