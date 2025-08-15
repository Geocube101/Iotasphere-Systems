from __future__ import annotations

import datetime
import flask
import json
import uuid

import CustomMethodsVI.Connection as Connection

import Admins
import Storage


class SocketioHandler:
    def __init__(self, app: flask.Flask, admin_cache: Admins.MyAdminCache, **kwargs):
        assert isinstance(app, flask.Flask)
        assert isinstance(admin_cache, Admins.MyAdminCache)

        self.__admin_cache__: Admins.MyAdminCache = admin_cache
        self.__app__: flask.Flask = app
        self.__socketio__: Connection.FlaskSocketioServer = Connection.FlaskSocketioServer(app, **kwargs)
        self.__admin_login_requests__: dict[int, datetime.datetime] = {}
        self.__setup__()

    def __setup__(self) -> None:
        admin: Connection.FlaskSocketioNamespace = self.__socketio__.of('/admin')

        @admin.on('connect')
        def onconnect(socket: Connection.FlaskSocketioSocket):
            if 'AuthToken' not in socket.request.cookies:
                socket.disconnect()
                return

            auth_token: uuid.UUID = uuid.UUID(int=int(socket.request.cookies['AuthToken'], 16), version=4)
            admin_info: Admins.MyAdminInfo | None = None

            @socket.on('disconnect')
            def on_disconnect(disconnector: bool) -> None:
                nonlocal admin_info

                if admin_info is not None:
                    admin_info.end_session()
                    print(f'Session End - {auth_token} @ {socket.ip_address}; {admin_info.concurrent_users()} active concurrent users')
                    admin_info = None

            @socket.on('request-begin-session')
            def on_begin_session_request() -> None:
                nonlocal admin_info
                admin_info = self.__admin_cache__.get_user_by_token(auth_token)
                success: bool = admin_info is not None
                socket.emit('begin-session-response', success, str(auth_token.int) if success else None)

                if success:
                    admin_info.begin_session()
                    print(f'Session Start - {auth_token} @ {socket.ip_address}; {admin_info.concurrent_users()} active concurrent users')

            @socket.on('session-tick')
            def on_session_tick(token: str) -> None:
                if token is None or token != str(auth_token.int) or not admin_info.session_active():
                    socket.disconnect()

            @socket.on('request-games-list')
            def on_games_list_request(token: str) -> None:
                if token is None or token != str(auth_token.int) or not admin_info.session_active():
                    socket.disconnect()
                    return

                socket.emit('games-list-response', json.dumps(Storage.MyGlobalServerStorage.STORAGE.send_dict(False)))

    def listen(self, host: str, port: int, async_: bool = False, **kwargs) -> None:
        if async_:
            self.__socketio__.async_listen(host, port, **kwargs)
        else:
            self.__socketio__.listen(host, port, **kwargs)

    def set_last_admin_login_attempt(self, ip: int, stamp: datetime.datetime) -> None:
        self.__admin_login_requests__[ip] = stamp

    def is_admin_session_active(self, token: uuid.UUID) -> bool:
        admin_info: Admins.MyAdminInfo = self.__admin_cache__.get_user_by_token(token)
        return admin_info is not None and admin_info.session_active()

    def get_session_admin_info(self, token: uuid.UUID) -> Admins.MyAdminInfo:
        return self.__admin_cache__.get_user_by_token(token)

    def get_last_admin_login_attempt(self, ip: int) -> datetime.datetime:
        return self.__admin_login_requests__[ip] if ip in self.__admin_login_requests__ else datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

    @property
    def socketio(self) -> Connection.FlaskSocketioServer:
        return self.__socketio__
