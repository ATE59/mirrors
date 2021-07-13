# coding=utf-8
import os

import time
from functools import wraps
from typing import (
    Dict,
    Any,
    AnyStr,
    Tuple,
    Optional,
)

from geoip2.errors import AddressNotFoundError

from db.db_engine import GeoIPEngine, AsnEngine
from api.exceptions import (
    BaseCustomException,
    AuthException,
)
from flask import (
    Response,
    jsonify,
    make_response,
    request,
)
from flask_api.status import HTTP_200_OK
from werkzeug.exceptions import InternalServerError


AUTH_KEY = os.environ.get('AUTH_KEY')


def jsonify_response(
        status: str,
        result: Dict[str, Any],
        status_code: int,
) -> Response:
    return make_response(
        jsonify(
            status=status,
            result=result,
            timestamp=int(time.time())
        ),
        status_code,
    )


def textify_response(
        content: AnyStr,
        status_code: int,
) -> Response:
    response = make_response(
        content,
        status_code,
    )
    response.mimetype = 'text/plain'
    return response


def auth_key_required(f):
    """
    Decorator: Check auth key
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'GET' or \
                AUTH_KEY == request.cookies.get('AUTH_KEY'):
            return f(*args, **kwargs)
        else:
            raise AuthException('Invalid auth key is passed')
    return decorated_function


def success_result(f):
    """
    Decorator: wrap success result
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = f(*args, **kwargs)
        if request.method == 'POST':
            return jsonify_response(
                status='success',
                result=result,
                status_code=HTTP_200_OK,
            )
        elif request.method == 'GET':
            return textify_response(
                content=result,
                status_code=HTTP_200_OK
            )

    return decorated_function


def error_result(f):
    """
    Decorator: catch unknown exceptions and raise InternalServerError
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except BaseCustomException:
            raise
        except Exception as err:
            raise InternalServerError(
                description=str(err),
                original_exception=err,
            )

    return decorated_function


def get_geo_data_by_ip(
        ip: AnyStr
) -> Optional[Tuple[AnyStr, AnyStr, float, float]]:
    """
    The function returns continent, country and locations of IP in English
    """

    db = GeoIPEngine.get_instance()
    try:
        city = db.city(ip)
    except AddressNotFoundError:
        return
    country = city.country.name
    continent = city.continent.name
    latitude = city.location.latitude
    longitude = city.location.longitude

    return continent, country, latitude, longitude


def get_asn_by_ip(
        ip: AnyStr,
) -> Optional[AnyStr]:
    """
    Get ASN by an IP
    """

    db = AsnEngine.get_instance()
    try:
        return db.asn(ip).autonomous_system_number
    except AddressNotFoundError:
        return
