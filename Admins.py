from __future__ import annotations

import base64
import Crypto.Cipher.AES
import PIL.Image
import cv2
import datetime
import io
import numpy
import os
import pickle
import re
import typing
import uuid

import CustomMethodsVI.FileSystem as FileSystem

import Util


class MyAdminInfo:
    SESSION_TIMEOUT_TIME: float = 300

    def __init__(self, token: int | uuid.UUID, access_type: Util.UserElevationType, enabled: bool, expires: float, username: str, email: str | None, password_buffer: bytes = None, *, user_icon: numpy.ndarray = None):
        self.__token__: uuid.UUID = token if isinstance(token, uuid.UUID) else uuid.UUID(int=token, version=4)
        self.__access_type__: Util.UserElevationType = Util.UserElevationType(access_type)
        self.__enabled__: bool = bool(enabled)
        self.__expires__: float = min(-1., float(expires))
        self.__username__: str = str(username)
        self.__usermail__: str | None = None if email is None else str(email)
        self.__buffer__: bytes = None if password_buffer is None else bytes(password_buffer)
        self.__user_icon__: bytes = None if user_icon is None else cv2.resize(user_icon, (256, 256, 3)).tobytes()
        self.__last_session__: tuple[datetime.datetime, float, int] | None = None

        assert len(self.__username__) >= 8, 'Username too short'
        assert re.fullmatch(r'[^@]+@[^@]+\.[^@]+', self.__usermail__), 'Invalid email'

    def set_password(self, password: str | None) -> None:
        if password is None:
            self.__buffer__ = None
            return

        _password: bytes = base64.b64encode(password.encode())
        remaining: int = max(0, 32 - len(_password))
        _password += b'\x00' * remaining
        _password = _password[:32]
        payload: bytes = self.__token__.int.to_bytes(64, 'big')
        crypter = Crypto.Cipher.AES.new(_password, Crypto.Cipher.AES.MODE_EAX)
        nonce: bytes = crypter.nonce
        cipher, mac = crypter.encrypt_and_digest(payload)
        self.__buffer__ = len(mac).to_bytes(8, 'big', signed=False) + len(nonce).to_bytes(8, 'little', signed=False) + mac + cipher + nonce

    def begin_session(self) -> None:
        now: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
        lst, _, cnt = (now, -1, 0) if self.__last_session__ is None else self.__last_session__
        self.__last_session__ = (lst if (now - lst).total_seconds() <= MyAdminInfo.SESSION_TIMEOUT_TIME or cnt > 0 else now, -1, cnt + 1)

    def end_session(self) -> None:
        assert self.session_active(), 'Session not in-progress'
        now: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
        lst, _, cnt = self.__last_session__
        self.__last_session__ = (lst, -1 if cnt >= 1 else (now - lst).total_seconds(), cnt - 1)

    def check_password(self, password: str) -> bool:
        if self.__buffer__ is None:
            return False

        _password: bytes = base64.b64encode(password.encode())
        remaining: int = max(0, 32 - len(_password))
        _password += b'\x00' * remaining
        _password = _password[:32]
        payload: bytes = self.__buffer__
        mac_length: int = int.from_bytes(payload[:8], 'big', signed=False)
        nonce_length: int = int.from_bytes(payload[8:16], 'little', signed=False)
        mac: bytes = payload[16:16 + mac_length]
        cipher: bytes = payload[16 + mac_length:-nonce_length]
        nonce: bytes = payload[-nonce_length:]
        crypter = Crypto.Cipher.AES.new(_password, Crypto.Cipher.AES.MODE_EAX, nonce=nonce)

        try:
            decoded: bytes = crypter.decrypt_and_verify(cipher, mac)

            if len(decoded) != 64:
                return False

            token: int = int.from_bytes(decoded, 'big')
            return token == self.__token__.int
        except ValueError:
            return False

    def session_active(self) -> bool:
        return self.__last_session__ is not None and self.__last_session__[1] == -1 and self.__last_session__[2] > 0

    def user_active(self) -> bool:
        return self.enabled and (not self.does_expire or self.expires > datetime.datetime.now(datetime.timezone.utc)) and self.__buffer__ is not None

    def concurrent_users(self) -> int:
        return self.__last_session__[2] if self.session_active() else 0

    def send_dict(self) -> dict[str, typing.Any]:
        return {
            'token': hex(self.__token__.int)[2:],
            'access-type': self.__access_type__.value,
            'enabled': self.__enabled__,
            'expires': None if self.__expires__ == -1 else self.__expires__ * 1000,
            'username': self.__username__,
            'usermail': self.__usermail__,
            'usericon': None if self.__user_icon__ is None else base64.b64encode(self.__user_icon__).decode(),
            'session': None if self.__last_session__ is None else {
                'start': self.__last_session__[0].timestamp() * 1000,
                'end': None if self.__last_session__[1] == -1 else self.__last_session__[1] * 1000,
                'active': self.__last_session__[2]
            }
        }

    @property
    def token(self) -> uuid.UUID:
        return self.__token__

    @property
    def does_expire(self) -> bool:
        return self.__expires__ != -1

    @property
    def enabled(self) -> bool:
        return self.__enabled__

    @property
    def access(self) -> Util.UserElevationType:
        return self.__access_type__

    @property
    def expires(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.__expires__, tz=datetime.timezone.utc)

    @property
    def username(self) -> str:
        return self.__username__

    @property
    def usermail(self) -> str:
        return self.__usermail__

    @property
    def usericon(self) -> PIL.Image.Image | None:
        return None if self.__user_icon__ is None else PIL.Image.open(io.BytesIO(self.__buffer__), 'r')

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self.__enabled__ = bool(value)

    @expires.setter
    def expires(self, expires: datetime.datetime | None) -> None:
        assert expires is None or isinstance(expires, datetime.datetime)

        if expires is None:
            self.__expires__ = -1
        else:
            self.__expires__ = expires.astimezone(datetime.timezone.utc).timestamp()

    @access.setter
    def access(self, access_level: int | Util.UserElevationType) -> None:
        self.__access_type__ = Util.UserElevationType(access_level)

    @username.setter
    def username(self, username: str) -> None:
        self.__username__ = str(username)
        assert len(self.__username__) >= 8, 'Username too short'

    @usermail.setter
    def usermail(self, email: str) -> None:
        self.__usermail__ = str(email)
        assert re.fullmatch(r'[^@]+@[^@]+\.[^@]+', self.__usermail__), 'Invalid email'

    @usericon.setter
    def usericon(self, icon: PIL.Image.Image | None) -> None:
        if icon is None:
            self.__user_icon__ = None
            return

        bytestream: io.BytesIO = io.BytesIO()
        icon.convert('RGB').save(bytestream, 'JPEG')
        self.__user_icon__ = bytestream.getvalue()


class MyAdminCache:
    @classmethod
    def load(cls, path: str) -> MyAdminCache:
        file: FileSystem.File = FileSystem.File(path)
        cache: MyAdminCache = cls()

        if file.exists():
            try:
                with file.open('rb') as f:
                    data: dict[uuid.UUID, MyAdminInfo] = pickle.load(f)

                now: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)

                for token, admin in data.items():
                    if token != admin.token or (admin.does_expire and admin.expires < now):
                        continue

                    while admin.session_active():
                        admin.end_session()

                    cache.__cache__[token] = admin

            except Exception as err:
                raise IOError('Failed to load user data') from err

        zero: uuid.UUID = uuid.UUID(int=0, version=4)

        if zero not in cache.__cache__ and os.name == 'nt':
            cache.add_user(Util.UserElevationType.SUPERUSER, True, -1, os.getenv('ROOTUSERNAME'), os.getenv('ROOTUSERMAIL'), os.getenv('ROOTPASSWORD'), token=zero)

        return cache

    def __init__(self):
        self.__cache__: dict[uuid.UUID, MyAdminInfo] = {}

    def save(self, path: str) -> None:
        file: FileSystem.File = FileSystem.File(path)

        try:
            for admin in self.__cache__.values():
                while admin.session_active():
                    admin.end_session()

            with file.open('wb') as f:
                pickle.dump(self.__cache__, f)
        except Exception as err:
            raise IOError('Failed to save user data') from err

    def del_user(self, token: uuid.UUID) -> None:
        if token in self.__cache__:
            del self.__cache__[token]

    def add_user(self, access_type: int | Util.UserElevationType, enabled: bool, expires: float, username: str, email: str | None, password: str | None, *, token: uuid.UUID = None) -> MyAdminInfo:
        assert isinstance(access_type, (int, Util.UserElevationType))
        assert isinstance(expires, (int, float))
        assert isinstance(username, str)
        assert email is None or isinstance(email, str)
        assert password is None or isinstance(password, str)
        assert token is None or isinstance(token, uuid.UUID)
        assert len(self.get_users_by_username(username)) == 0, f'User with username \'{username}\' already exists'
        assert len(self.get_users_by_usermail(email)) == 0, f'User with email \'{email}\' already exists'
        assert password is None or len(password) >= 8, 'Password length too short'

        token = uuid.uuid4() if token is None else token

        while token in self.__cache__:
            token = uuid.uuid4()

        user: MyAdminInfo = MyAdminInfo(token, Util.UserElevationType(access_type), enabled, expires, username, email)
        user.set_password(password)
        self.__cache__[token] = user
        return user

    def get_user_by_token(self, token: uuid.UUID) -> MyAdminInfo | None:
        assert isinstance(token, uuid.UUID)
        return self.__cache__[token] if token in self.__cache__ else None

    def get_users_by_username(self, username: str) -> tuple[MyAdminInfo, ...]:
        assert isinstance(username, str)
        return tuple(user for user in self.__cache__.values() if user.username == username)

    def get_users_by_usermail(self, email: str) -> tuple[MyAdminInfo, ...]:
        assert isinstance(email, str)
        return tuple(user for user in self.__cache__.values() if user.usermail == email)

    def send_users(self) -> dict[str, dict]:
        return {hex(userid.int)[2:]: info.send_dict() for userid, info in self.__cache__.items()}
