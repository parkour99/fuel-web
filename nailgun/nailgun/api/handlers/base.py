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

from datetime import datetime
from decorator import decorator
import json

import web

from nailgun.api.serializers.base import BasicSerializer
from nailgun.api.validators.base import BasicValidator
from nailgun.db import db
from nailgun.errors import errors
from nailgun.logger import logger
from nailgun import notifier


def check_client_content_type(handler):
    content_type = web.ctx.env.get("CONTENT_TYPE", "application/json")
    if web.ctx.path.startswith("/api")\
            and not content_type.startswith("application/json"):
        raise web.unsupportedmediatype
    return handler()


def forbid_client_caching(handler):
    if web.ctx.path.startswith("/api"):
        web.header('Cache-Control',
                   'store, no-cache, must-revalidate,'
                   ' post-check=0, pre-check=0')
        web.header('Pragma', 'no-cache')
        dt = datetime.fromtimestamp(0).strftime(
            '%a, %d %b %Y %H:%M:%S GMT'
        )
        web.header('Expires', dt)
    return handler()


@decorator
def content_json(func, *args, **kwargs):
    try:
        data = func(*args, **kwargs)
    except web.notmodified:
        raise
    except web.HTTPError as http_error:
        web.header('Content-Type', 'application/json')
        if isinstance(http_error.data, (dict, list)):
            http_error.data = build_json_response(http_error.data)
        raise
    web.header('Content-Type', 'application/json')
    return build_json_response(data)


def build_json_response(data):
    web.header('Content-Type', 'application/json')
    if type(data) in (dict, list):
        return json.dumps(data)
    return data


class BaseHandler(object):
    validator = BasicValidator
    serializer = BasicSerializer

    fields = []

    @classmethod
    def render(cls, instance, fields=None):
        return cls.serializer.serialize(
            instance,
            fields=fields or cls.fields
        )

    def checked_data(self, validate_method=None, **kwargs):
        try:
            data = kwargs.pop('data', web.data())
            method = validate_method or self.validator.validate

            valid_data = method(data, **kwargs)
        except (
            errors.InvalidInterfacesInfo,
            errors.InvalidMetadata
        ) as exc:
            notifier.notify("error", str(exc))
            raise web.badrequest(message=str(exc))
        except (
            errors.AlreadyExists
        ) as exc:
            err = web.conflict()
            err.message = exc.message
            raise err
        except (
            errors.InvalidData,
            Exception
        ) as exc:
            raise web.badrequest(message=str(exc))
        return valid_data

    def get_object_or_404(self, model, *args, **kwargs):
        # should be in ('warning', 'Log message') format
        # (loglevel, message)
        log_404 = kwargs.pop("log_404") if "log_404" in kwargs else None
        log_get = kwargs.pop("log_get") if "log_get" in kwargs else None
        if "id" in kwargs:
            obj = db().query(model).get(kwargs["id"])
        elif len(args) > 0:
            obj = db().query(model).get(args[0])
        else:
            obj = db().query(model).filter(**kwargs).all()
        if not obj:
            if log_404:
                getattr(logger, log_404[0])(log_404[1])
            raise web.notfound('{0} not found'.format(model.__name__))
        else:
            if log_get:
                getattr(logger, log_get[0])(log_get[1])
        return obj

    def get_objects_list_or_404(self, model, ids):
        """Get list of objects

        :param model: model object
        :param ids: list of ids

        :raises: web.notfound
        :returns: query object
        """
        node_query = db.query(model).filter(model.id.in_(ids))
        objects_count = node_query.count()

        if len(set(ids)) != objects_count:
            raise web.notfound('{0} not found'.format(model.__name__))

        return node_query


class SingleHandler(BaseHandler):

    validator = BasicValidator
    single = None

    @content_json
    def GET(self, obj_id):
        """:returns: JSONized REST object.
        :http: * 200 (OK)
               * 404 (object not found in db)
        """
        obj = self.get_object_or_404(
            self.single.model,
            obj_id
        )
        return self.single.to_json(obj)

    @content_json
    def PUT(self, obj_id):
        """:returns: JSONized REST object.
        :http: * 200 (OK)
               * 404 (object not found in db)
        """
        obj = self.get_object_or_404(
            self.single.model,
            obj_id
        )

        try:
            data = self.checked_data(
                self.validator.validate_update,
                instance=obj
            )
        except (errors.AlreadyExists, errors.InvalidData) as exc:
            raise web.badrequest(str(exc))

        self.single.update(obj, data)
        return self.single.to_json(obj)

    def DELETE(self, obj_id):
        """:returns: Empty string
        :http: * 204 (object successfully deleted)
               * 404 (object not found in db)
        """
        obj = self.get_object_or_404(
            self.single.model,
            obj_id
        )

        try:
            self.validator.validate_delete(obj)
        except errors.CannotDelete as exc:
            raise web.badrequest(str(exc))

        self.single.delete(obj)
        raise web.webapi.HTTPError(
            status="204 No Content",
            data=""
        )


class CollectionHandler(BaseHandler):

    validator = BasicValidator
    collection = None

    @content_json
    def GET(self):
        """:returns: Collection of JSONized REST objects.
        :http: * 200 (OK)
        """
        return self.collection.to_json()

    @content_json
    def POST(self):
        """:returns: JSONized REST object.
        :http: * 201 (object successfully created)
               * 400 (invalid object data specified)
               * 409 (object with such parameters already exists)
        """
        data = self.checked_data()
        new_obj = self.collection.create(data)
        return web.webapi.created(
            self.collection.single.to_json(new_obj)
        )