import base64
import datetime
import flask
import io
import json
import multiprocessing
import multiprocessing.connection
import os
import PIL.Image
import requests
import requests.structures
import signal
import threading
import traceback
import time
import typing
import uuid

import CustomMethodsVI.FileSystem as FileSystem
import CustomMethodsVI.Stream as Stream

import Admins
import Storage
import Util
import SocketHandler
import Subserver

flask_app: flask.Flask = flask.Flask(__name__, template_folder='templates')
flask_app.config['MAX_FORM_MEMORY_SIZE'] = 10 * 2 ** 20
admin_cache: Admins.MyAdminCache = Admins.MyAdminCache.load('Data/admin.dat')
executable_dir: FileSystem.Directory = FileSystem.Directory('Executables')
external_executable_file: FileSystem.File = executable_dir.file('executables.json')
storage: Storage.MyGlobalServerStorage = Storage.MyGlobalServerStorage.load('Data/storage.json')
socketio: SocketHandler.SocketioHandler = SocketHandler.SocketioHandler(flask_app, admin_cache, async_mode='gevent')
executables: dict[str, tuple[int, tuple[str, str], multiprocessing.Process, multiprocessing.connection.Connection, multiprocessing.connection.Connection]] = {}
temp_program_listings: dict[str, str] = {}
HOST: str = '0.0.0.0'
SCHEMA: str = 'http://'
PORT: int = 5000

if not executable_dir.exists():
    executable_dir.create()


@flask_app.after_request
def apply_headers(response: flask.Response):
    if 'is-iota-proxy' in response.headers:
        del response.headers['is-iota-proxy']
        return response

    response.headers['Content-Security-Policy'] = "default-src https: 'self'; img-src https: data: blob: *"
    response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


@flask_app.route('/')
def index():
    return flask.render_template('index.html')


@flask_app.route('/proxyhost/<path:subdomain>', methods=('GET', 'POST'))
def proxyhost(subdomain: str):
    parts: list[str] = subdomain.split('/', 1)
    subdomain = parts[0]
    subpath: str = '' if len(parts) == 1 else parts[1].lstrip('/')

    if subdomain not in executables:
        return flask.Response(status=404)

    subport: int = executables[subdomain][0]
    subroot, substatic = executables[subdomain][1]
    header: str = f'proxyhost/{subdomain}/'

    if subpath.startswith(header):
        subpath = subpath[len(header):]

    root: str = substatic if subpath.startswith('static/') else subroot
    proxy: requests.Response = requests.request(method=flask.request.method, url=f'{SCHEMA}127.0.0.1:{subport}{root}{f'/{subpath.lstrip('/')}'}'.rstrip('/'), headers=flask.request.headers, cookies=flask.request.cookies, allow_redirects=False, data=flask.request.get_data())
    headers: requests.structures.CaseInsensitiveDict[str] = proxy.headers
    headers['is-iota-proxy'] = '1'
    return flask.Response(response=proxy.content, status=proxy.status_code, headers=headers)


@flask_app.route('/fileshare/<path:filepath>', methods=('GET', 'POST'))
def fileshare(filepath: str):
    basedir: FileSystem.Directory = FileSystem.Directory('Data/fileshare')
    file: FileSystem.File = basedir.file(filepath)
    abspath1: str = basedir.abspath()
    abspath2: str = file.parentdir().abspath()
    return flask.send_from_directory(file.parentdir().dirpath(), file.basename()) if abspath2.startswith(abspath1) and file.exists() else flask.Response(status=404, response='No such file')


@flask_app.route('/admin', methods=('GET',))
def admin():
    if 'AuthToken' not in flask.request.cookies:
        return flask.redirect('/?adminlogin=1')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)
    admin_info: Admins.MyAdminInfo = admin_cache.get_user_by_token(token)

    if admin_info is None or not admin_info.user_active():
        return flask.redirect('/?adminlogin=1&prompt=No Such User')

    return flask.render_template('admin.html')


@flask_app.route('/admin-login', methods=('POST',))
def admin_login():
    ip, is_ipv6 = Util.get_addr_ipv4_ipv6(flask.request.remote_addr)
    now: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)

    if ip == -1 or is_ipv6 is None:
        return flask.Response(status=400)
    elif (now - socketio.get_last_admin_login_attempt(ip)).total_seconds() <= 30:
        socketio.set_last_admin_login_attempt(ip, now)
        return flask.Response(status=429)

    socketio.set_last_admin_login_attempt(ip, now)
    username: str = flask.request.form.get('username')
    password: str = flask.request.form.get('password')
    is_ip_perm: bool = flask.request.form.get('remember-ip') == 'true'
    admin_info: Admins.MyAdminInfo = Stream.LinqStream(admin_cache.get_users_by_username(username)).merge(admin_cache.get_users_by_usermail(username)).filter(lambda info: info.check_password(password)).first_or_default(None)

    if admin_info is None or username is None or password is None:
        return flask.Response(status=401)

    token: int = admin_info.token.int
    response: flask.Response = flask.redirect('/admin')
    response.headers['Set-Cookie'] = f'AuthToken={hex(token)[2:]}; Path=/; HttpOnly; SameSite=Strict; Secure; Partitioned; Max-Age={86400 if is_ip_perm else 3600}'
    return response


@flask_app.route('/admin/games-list', methods=('POST',))
def admin_games_list():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.content_type != 'application/json' or flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')

    return flask.Response(status=200, response=json.dumps(storage.send_dict(False)['game-storage']))


@flask_app.route('/admin/programs-list', methods=('POST',))
def admin_programs_list():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.content_type != 'application/json' or flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')

    return flask.Response(status=200, response=json.dumps(storage.send_dict(False)['program-storage']))


@flask_app.route('/admin/users-list', methods=('POST',))
def admin_users_list():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.content_type != 'application/json' or flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')

    return flask.Response(status=200, response=json.dumps(admin_cache.send_users()))


@flask_app.route('/admin/contacts-list', methods=('POST',))
def admin_contacts_list():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.content_type != 'application/json' or flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')

    return flask.Response(status=200, response=json.dumps(storage.send_dict(False)['contact-storage']))


@flask_app.route('/admin/games-add', methods=('POST',))
def admin_games_add():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')

    display_name: str = f'new_game_{uuid.uuid4()}'
    name: str = Util.to_functional_name(display_name)

    while storage.get_game(name) is not None:
        display_name = f'new_game_{uuid.uuid4()}'
        name = Util.to_functional_name(display_name)

    storage.add_game(name)
    return flask.Response(status=200, response=json.dumps({'new': name, 'body': storage.send_dict(False)['game-storage']}), headers={'Content-Type': 'application/json'})


@flask_app.route('/admin/programs-add', methods=('POST',))
def admin_programs_add():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')

    display_name: str = f'new_program_{uuid.uuid4()}'
    name: str = Util.to_functional_name(display_name)

    while storage.get_program(name) is not None:
        display_name = f'new_program_{uuid.uuid4()}'
        name = Util.to_functional_name(display_name)

    storage.add_program(name)
    return flask.Response(status=200, response=json.dumps({'new': name, 'body': storage.send_dict(False)['program-storage']}), headers={'Content-Type': 'application/json'})


@flask_app.route('/admin/users-add', methods=('POST',))
def admin_users_add():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')
    elif socketio.get_session_admin_info(token).access > Util.UserElevationType.ADMINISTRATOR:
        return flask.Response(status=403, response='Insufficient Permissions')

    new_user: Admins.MyAdminInfo = admin_cache.add_user(Util.UserElevationType.MODERATOR, False, -1, '', None, None)
    new_token: uuid.UUID = new_user.token
    return flask.Response(status=200, response=json.dumps({'new': str(new_token.int), 'body': admin_cache.send_users()}), headers={'Content-Type': 'application/json'})


@flask_app.route('/admin/contacts-add', methods=('POST',))
def admin_contacts_add():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')

    display_name: str = f'new_contact_{uuid.uuid4()}'
    name: str = Util.to_functional_name(display_name)

    while storage.get_contact(name) is not None:
        display_name = f'new_game_{uuid.uuid4()}'
        name = Util.to_functional_name(display_name)

    storage.add_contact(name)
    return flask.Response(status=200, response=json.dumps({'new': name, 'body': storage.send_dict(False)['contact-storage']}), headers={'Content-Type': 'application/json'})


@flask_app.route('/admin/games-del', methods=('POST',))
def admin_games_del():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')
    elif socketio.get_session_admin_info(token).access > Util.UserElevationType.ADMINISTRATOR:
        return flask.Response(status=403, response='Insufficient Permissions')

    storage.del_game(flask.request.json['game-id'])
    return flask.Response(status=200, response=json.dumps(storage.send_dict(False)['game-storage']), headers={'Content-Type': 'application/json'})


@flask_app.route('/admin/programs-del', methods=('POST',))
def admin_programs_del():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')
    elif socketio.get_session_admin_info(token).access > Util.UserElevationType.ADMINISTRATOR:
        return flask.Response(status=403, response='Insufficient Permissions')

    storage.del_program(flask.request.json['program-id'])
    return flask.Response(status=200, response=json.dumps(storage.send_dict(False)['program-storage']), headers={'Content-Type': 'application/json'})


@flask_app.route('/admin/users-del', methods=('POST',))
def admin_users_del():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)
    user_info: Admins.MyAdminInfo

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')
    elif (user_info := socketio.get_session_admin_info(token)).access > Util.UserElevationType.ADMINISTRATOR:
        return flask.Response(status=403, response='Insufficient Permissions')

    target_id: uuid.UUID = uuid.UUID(int=int(flask.request.json['user-id'], 16), version=4)
    target: Admins.MyAdminInfo = admin_cache.get_user_by_token(target_id)

    if target.access < user_info.access:
        return flask.Response(status=403, response='Insufficient Permissions')

    admin_cache.del_user(target_id)
    return flask.Response(status=200, response=json.dumps(storage.send_dict(False)['program-storage']), headers={'Content-Type': 'application/json'})


@flask_app.route('/admin/contacts-del', methods=('POST',))
def admin_contacts_del():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')
    elif socketio.get_session_admin_info(token).access > Util.UserElevationType.ADMINISTRATOR:
        return flask.Response(status=403, response='Insufficient Permissions')

    storage.del_contact(flask.request.json['contact-id'])
    return flask.Response(status=200, response=json.dumps(storage.send_dict(False)['contact-storage']), headers={'Content-Type': 'application/json'})


@flask_app.route('/admin/game-editor', methods=('POST',))
def admin_game_editor():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')
    elif socketio.get_session_admin_info(token).access > Util.UserElevationType.ADMINISTRATOR:
        return flask.Response(status=403, response='Insufficient Permissions')

    game: Storage.MyGameStorageInfo = storage.get_game(flask.request.form.get('game-editor-game-id'))

    if game is not None:
        url: str | None = flask.request.form.get('game-editor-game-url') if 'game-editor-game-url' in flask.request.form else None
        game.display_name = flask.request.form.get('game-editor-game-name')
        game.url = None if url is None or len(url) == 0 else url
        game.visible = 'game-editor-game-visible' in flask.request.form and flask.request.form.get('game-editor-game-visible') == 'true'
        icon_image_data: str = flask.request.form.get('game-editor-game-icon-image-data')
        background_image_data: str = flask.request.form.get('game-editor-game-bg-image-data')
        section_data: dict = json.loads(flask.request.form.get('game-editor-game-sections'))

        if len(icon_image_data) > 0:
            bytestream: io.BytesIO = io.BytesIO(base64.b64decode(icon_image_data))
            image: PIL.Image.Image = PIL.Image.open(bytestream, 'r')
            game.icon_image = image

        if len(background_image_data) > 0:
            bytestream: io.BytesIO = io.BytesIO(base64.b64decode(background_image_data))
            image: PIL.Image.Image = PIL.Image.open(bytestream, 'r')
            game.background_image = image

        for section_name, section_data in section_data.items():
            if section_data is None:
                game.del_section(section_name)
                continue

            section: Storage.MyGameStorageInfo.MyGameSectionInfo = game.get_section(section_name)
            visible: bool = section_data['visible']
            display_name: str = section_data['display-name']
            new_background_image: str | None = section_data['new-background-image']
            children: dict = section_data['children']
            background_image: int | None = None

            if len(new_background_image):
                bytestream: io.BytesIO = io.BytesIO(base64.b64decode(new_background_image))
                image: PIL.Image.Image = PIL.Image.open(bytestream, 'r')
                background_image = storage.MyImageLoader.MyBackgroundStorage.set_image(None, image)

            if section is None:
                section = game.add_section(Util.to_functional_name(display_name), display_name, background_image, visible)
            else:
                section.display_name = display_name
                section.background_image = background_image
                section.visible = visible

            for child_name, child_data in children.items():
                if child_data is None:
                    section.del_child(child_name)
                    continue

                child: Storage.MyGameStorageInfo.MyGameObjectInfo = section.get_child(child_name)
                child_display_name: str = child_data['display-name']
                child_url: str = child_data['url']
                child_visible: bool = child_data['visible']
                new_child_icon_image: str = child_data['new-icon-image']
                child_icon_image: int | None = None

                if len(new_child_icon_image):
                    bytestream: io.BytesIO = io.BytesIO(base64.b64decode(new_child_icon_image))
                    image: PIL.Image.Image = PIL.Image.open(bytestream, 'r')
                    child_icon_image = storage.MyImageLoader.MyIconStorage.set_image(None, image)

                if child is None:
                    section.add_child(Util.to_functional_name(child_display_name), child_display_name, child_url, child_icon_image, child_visible)
                else:
                    child.display_name = child_display_name
                    child.url = child_url
                    child.icon_image = child_icon_image
                    child.visible = child_visible
    else:
        return flask.Response(status=404, response='Specified game does not exist')

    return flask.redirect('/admin', 302)


@flask_app.route('/admin/program-editor', methods=('POST',))
def admin_program_editor():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')
    elif socketio.get_session_admin_info(token).access > Util.UserElevationType.ADMINISTRATOR:
        return flask.Response(status=403, response='Insufficient Permissions')

    program: Storage.MyProgramStorageInfo = storage.get_program(flask.request.form.get('program-editor-program-id'))

    if program is not None:
        url: str | None = flask.request.form.get('program-editor-program-url') if 'program-editor-program-url' in flask.request.form else None
        program.display_name = flask.request.form.get('program-editor-program-name')
        program.url = None if url is None or len(url) == 0 else url
        program.visible = 'program-editor-program-visible' in flask.request.form and flask.request.form.get('program-editor-program-visible') == 'true'
        width: int = int(flask.request.form.get('program-editor-program-width'))
        height: int = int(flask.request.form.get('program-editor-program-height'))
        program_type: int = int(flask.request.form.get('program-editor-program-type'))
        program.dimensions = (width if 0 < width <= 5 else None, height if 0 < height <= 5 else None)
        program.program_type = Stream.LinqStream(iter(Util.ProgramType)).filter(lambda enum: enum.value == program_type).first_or_default(Util.ProgramType.PROGRAM)
        icon_image_data: str = flask.request.form.get('program-editor-program-icon-image-data')

        if len(icon_image_data) > 0:
            bytestream: io.BytesIO = io.BytesIO(base64.b64decode(icon_image_data))
            image: PIL.Image.Image = PIL.Image.open(bytestream, 'r')
            program.icon_image = image
    else:
        return flask.Response(status=404, response='Specified program does not exist')


    return flask.redirect('/admin', 302)


@flask_app.route('/admin/user-editor', methods=('POST',))
def admin_user_editor():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)
    this_user: Admins.MyAdminInfo

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')
    elif (this_user := socketio.get_session_admin_info(token)).access > Util.UserElevationType.MODERATOR:
        return flask.Response(status=403, response='Insufficient Permissions')

    target_user: Admins.MyAdminInfo = admin_cache.get_user_by_token(uuid.UUID(int=int(flask.request.form.get('user-editor-user-id'), 16), version=4))

    if target_user is not None:
        target_user.username = flask.request.form.get('user-editor-user-name')
        target_user.usermail = flask.request.form.get('user-editor-user-email')
        does_expire: bool = 'user-editor-user-expires' in flask.request.form and flask.request.form.get('user-editor-user-expires') == 'true'
        target_user.expires = datetime.datetime.fromtimestamp(float(flask.request.form.get('user-editor-user-expire-ts')) / 1000, datetime.timezone.utc) if does_expire else None
        target_user.enabled = 'user-editor-user-enabled' in flask.request.form and flask.request.form.get('user-editor-user-enabled') == 'true'
        access_type: int = int(flask.request.form.get('user-editor-user-type'))

        if access_type < this_user.access.value:
            return flask.Response(status=403, response='Insufficient Permissions')

        target_user.access = Stream.LinqStream(iter(Util.UserElevationType)).filter(lambda enum: enum.value == access_type).first_or_default(Util.UserElevationType.MODERATOR)
        icon_image_data: str = flask.request.form.get('user-editor-user-icon-image-data')

        if len(icon_image_data) > 0:
            bytestream: io.BytesIO = io.BytesIO(base64.b64decode(icon_image_data))
            image: PIL.Image.Image = PIL.Image.open(bytestream, 'r')
            target_user.usericon = image
    else:
        return flask.Response(status=404, response='Specified user does not exist')

    return flask.redirect('/admin', 302)


@flask_app.route('/admin/contact-editor', methods=('POST',))
def admin_contact_editor():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)

    if flask.request.user_agent.string == '' or not socketio.is_admin_session_active(token):
        return flask.Response(status=401, response='Invalid Session')
    elif socketio.get_session_admin_info(token).access > Util.UserElevationType.ADMINISTRATOR:
        return flask.Response(status=403, response='Insufficient Permissions')

    contact: Storage.MyContactStorageInfo = storage.get_contact(flask.request.form.get('contact-editor-contact-id'))

    if contact is not None:
        contact.contact_type = int(flask.request.form.get('contact-editor-contact-type'), 10)
        contact.content = flask.request.form.get('contact-editor-contact-content') if 'contact-editor-contact-content' in flask.request.form else None
        contact.display_name = flask.request.form.get('contact-editor-contact-name')
        contact.visible = 'contact-editor-contact-visible' in flask.request.form and flask.request.form.get('contact-editor-contact-visible') == 'true'
        icon_image_data: str = flask.request.form.get('contact-editor-contact-icon-image-data')

        if len(icon_image_data) > 0:
            bytestream: io.BytesIO = io.BytesIO(base64.b64decode(icon_image_data))
            image: PIL.Image.Image = PIL.Image.open(bytestream, 'r')
            contact.icon_image = image
    else:
        return flask.Response(status=404, response='Specified contact does not exist')


    return flask.redirect('/admin', 302)


@flask_app.route('/admin/current-user', methods=('POST',))
def admin_current_user():
    if 'AuthToken' not in flask.request.cookies:
        return flask.Response(status=401, response='Unauthorized')

    cookie: str = flask.request.cookies['AuthToken']
    token: uuid.UUID = uuid.UUID(int=int(cookie, 16), version=4)
    user_info: Admins.MyAdminInfo = socketio.get_session_admin_info(token)

    if flask.request.user_agent.string == '' or user_info is None:
        return flask.Response(status=401, response='Invalid Session')

    return flask.Response(response=json.dumps(user_info.send_dict()), status=200, headers={'Content-Type': 'application/json'})


@flask_app.route('/connect-init', methods=('POST',))
def connect_init():
    request: flask.Request = flask.request

    if request.content_type != 'application/json' or request.user_agent.string == '':
        return flask.Response(status=401)

    return flask.Response(status=200, response=json.dumps(storage.send_dict()))


@flask_app.route('/image/icon/<path:image_id>', methods=('GET', 'POST',))
def icon_image(image_id: str):
    if flask.request.user_agent.string == '':
        return flask.Response(status=401)
    elif not image_id.isnumeric():
        return flask.Response(status=400)

    image_id: int = int(image_id, 10)
    file: FileSystem.File | None = storage.MyImageLoader.MyIconStorage.image_file(image_id)
    response: flask.Response = flask.Response(status=404, response=f'No such image: {image_id}') if file is None else flask.send_from_directory(storage.MyImageLoader.MyIconStorage.dir.dirpath(), file.basename())
    response.headers['Cache-Control'] = 'no-store'
    return response


@flask_app.route('/image/background/<path:image_id>', methods=('GET', 'POST',))
def background_image(image_id: str):
    if flask.request.user_agent.string == '':
        return flask.Response(status=401)
    elif not image_id.isnumeric():
        return flask.Response(status=400)

    image_id: int = int(image_id, 10)
    file: FileSystem.File | None = storage.MyImageLoader.MyBackgroundStorage.image_file(image_id)
    response: flask.Response = flask.Response(status=404, response=f'No such image: {image_id}') if file is None else flask.send_from_directory(storage.MyImageLoader.MyBackgroundStorage.dir.dirpath(), file.basename())
    response.headers['Cache-Control'] = 'no-store'
    return response


@flask_app.route('/image/generic/<path:image_id>', methods=('GET', 'POST',))
def generic_image(image_id: str):
    if flask.request.user_agent.string == '':
        return flask.Response(status=401)
    elif not image_id.isnumeric():
        return flask.Response(status=400)

    image_id: int = int(image_id, 10)
    file: FileSystem.File | None = storage.MyImageLoader.MyGenericStorage.image_file(image_id)
    response: flask.Response = flask.Response(status=404, response=f'No such image: {image_id}') if file is None else flask.send_from_directory(storage.MyImageLoader.MyGenericStorage.dir.dirpath(), file.basename())
    response.headers['Cache-Control'] = 'no-store'
    return response


@flask_app.route('/shutdown', methods=('POST',))
def shutdown():
    if flask.request.remote_addr == '127.0.0.1':
        try:
            for route, (subport, subroots, process, stdout, stderr) in executables.items():
                pid: int | None = None

                if process.is_alive():
                    pid = process.pid
                    os.kill(process.pid, signal.SIGINT)
                    process.join(1)

                    if process.is_alive():
                        process.terminate()

                print(f'\033[38;2;150;0;0m ... [X] Closed sub-server @ {route}:{subport} with PID={pid}\033[0m')
        except (SystemExit, KeyboardInterrupt):
            print(f'\033[38;2;150;0;0m [X] Unlawful server termination\033[0m')

            for route, (subport, process) in executables.items():
                if process.is_alive():
                    process.terminate()

        for subdomain, program in temp_program_listings.items():
            storage.del_program(program)

        executables.clear()
        storage.save('Data/storage.json')
        admin_cache.save('Data/admin.dat')
        socketio.socketio.socketio.stop()
        print('\033[38;2;255;0;0m [X] Server Closed\033[0m\n')
        return flask.Response(status=200)
    else:
        return flask.Response(status=404)


@flask_app.route('/<path:urlpath>', methods=('GET', 'POST'))
def fallback(urlpath):
    referer: str = flask.request.headers.get('Referer')
    parts: list[str] = referer[referer.index('://') + 3:].split('/') if 'Referer' in flask.request.headers and referer is not None and '://' in referer else None
    proxy: int = parts.index('proxyhost') if parts is not None and 'proxyhost' in parts else -1
    subdomain: str = parts[proxy + 1] if proxy != -1 and len(parts) > proxy else None

    if referer is None or proxy == -1 or subdomain is None or subdomain not in executables:
        return flask.Response(status=404)
    else:
        subpath: str = flask.request.url.split('://')[1].split('/')[1]
        print(subdomain, subpath)
        return flask.redirect(f'/proxyhost/{subdomain}/{subpath}', 307)


def load_executables(host: str, port: int):
    print('\033[38;2;50;50;255m [*] Loading Executables...\033[0m')
    used_ports: list[int] = [port]
    events: list[threading.Event] = []
    data: dict[str, typing.Any] = {}
    listing: list[str] = []

    if external_executable_file.exists():

        with external_executable_file.open('r') as f:
            data = json.load(f)

            for route_name, executable in data.items():
                if len(route_name) < 4:
                    print(f'\033[38;5;214m ... [!] Routing path to short: "{executable_path}" @ {route_name}\033[0m')
                    continue

                executable_path: str = executable['executable']
                subport: int = executable['port'] if port in executable else port + len(used_ports)
                root: str = '/' if 'root' not in executable or executable['root'] is None else f'/{str(executable['root']).lstrip('/')}'
                static: str = '/' if 'static' not in executable or executable['static'] is None else f'/{str(executable['static']).lstrip('/')}'

                if subport in used_ports:
                    print(f'\033[38;5;214m ... [!] Failed to assign unique port: "{executable_path}" @ {subport}\033[0m')
                    continue
                else:
                    used_ports.append(subport)

                if not os.path.exists(executable_path):
                    print(f'\033[38;5;214m ... [!] Failed to locate executable: "{executable_path}"\033[0m')
                    continue

                try:
                    event: threading.Event = multiprocessing.Event()
                    event.clear()
                    events.append(event)
                    stdout_recv, stdout_send = multiprocessing.Pipe(False)
                    stderr_recv, stderr_send = multiprocessing.Pipe(False)
                    process: multiprocessing.Process = multiprocessing.Process(target=Subserver.spawn_subserver, args=(event, host, route_name, executable_path, subport, stdout_send, stderr_send))
                    executables[route_name] = (subport, (root, static), process, stdout_recv, stderr_recv)
                    process.start()

                    if 'width' in executable and 'height' in executable:
                        listing.append(route_name)

                    print(f'\033[38;2;0;150;0m ... [+] Started sub-server \"{executable_path}\" @ {route_name}:{subport} with PID={process.pid}\033[0m')
                except Exception as err:
                    print(f'\033[38;5;214m ... [!] Failed to start subserver: "{executable_path}" --> {err}\033[0m')

    while any(not event.is_set() for event in events):
        time.sleep(1e-3)

    closed: list[str] = []

    for subdomain, (subport, subroots, process, stdout, stderr) in executables.items():
        if not process.is_alive():
            closed.append(subdomain)
            continue
        elif subdomain not in listing or subdomain not in data:
            continue

        program: Storage.MyProgramStorageInfo = storage.add_program(subdomain)
        program.url = f'/proxyhost/{subdomain}'
        program.dimensions = (data[subdomain]['width'], data[subdomain]['height'])
        program.program_type = Util.ProgramType.WEBSITE
        program.visible = True
        program.display_name = data[subdomain].get('display-name') or 'N/A'
        temp_program_listings[subdomain] = program.name

    for close in closed:
        del executables[close]

    print(f'\033[38;2;0;150;0m [+] Loaded {len(executables)} Executable(s)\033[0m')


def main():
    load_executables(HOST, PORT)
    socketio.listen(HOST, PORT, True)
    print('\033[38;2;0;255;0m [+] Server Started\033[0m')

    try:
        closed: list[str] = []

        while not socketio.socketio.closed:
            for subdomain, (subport, subroots, process, stdout, stderr) in executables.items():
                if not process.is_alive():
                    if subdomain not in closed:
                        closed.append(subdomain)
                    continue

                try:
                    while not stdout.closed and stdout.poll(0):
                        print(f'\033[38;2;50;50;255m ... [*] [{process.pid}]\033[0m - {stdout.recv()}', end='')

                    while not stderr.closed and stderr.poll(0):
                        print(f'\033[38;2;255;50;50m ... [!] [{process.pid}]\033[38;2;255;100;100m - {stderr.recv()}\033[0m', end='')
                except (BrokenPipeError, IOError) as err:
                    print(f'\033[38;5;214m [!] Sub-server standard pipe closed @ {subdomain}:{executables[subdomain][0]} with PID={executables[subdomain][2].pid}\n\t...\nERROR={type(err).__name__}\033[0m')
                    os.kill(process.pid, signal.SIGINT)
                    process.join(1)

                    if process.is_alive():
                        process.terminate()

            for subdomain in closed:
                print(f'\033[38;2;255;50;50m [X] Sub-server closed @ {subdomain}:{executables[subdomain][0]} with PID={executables[subdomain][2].pid}')
                del executables[subdomain]

            closed.clear()
            time.sleep(1e-2)
    except (SystemExit, KeyboardInterrupt):
        print('\033[38;5;214m [!] Closing Server...\033[0m')
        response: requests.Response = requests.post(f'{SCHEMA}localhost:{PORT}/shutdown')

        if not response.ok:
            raise IOError('Failed to cleanly shutdown server')
    except Exception as e:
        print(f'\033[38;2;255;50;50m ... [X] [{os.getpid()}] - Critical error during server runtime!\n\t ...\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}\033[0m')
        response: requests.Response = requests.post(f'{SCHEMA}localhost:{PORT}/shutdown')

        if not response.ok:
            raise IOError('Failed to cleanly shutdown server')


if not __name__.startswith('__mp_'):
    main()
