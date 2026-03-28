import datetime
import flask
import typing


import CustomMethodsVI.Connection as Connection


def handler(app: flask.Flask) -> None:
    api: Connection.FlaskServerAPI = Connection.FlaskServerAPI(app)
