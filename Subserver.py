import flask
import gevent
import gevent.pywsgi
import importlib
import importlib.machinery
import importlib.util
import multiprocessing
import multiprocessing.connection
import os
import sys
import threading
import traceback
import types
import typing
import werkzeug.routing

import CustomMethodsVI.Connection as Connection
import CustomMethodsVI.Stream as Stream


class SubserverConsoleWriter(Stream.StringStream):
    def __init__(self, pipe: multiprocessing.connection.Connection):
        super().__init__()
        assert isinstance(pipe, multiprocessing.connection.PipeConnection) if 'PipeConnection' in dir(multiprocessing.connection) else isinstance(pipe, multiprocessing.connection.Connection)
        self.__pipe__: multiprocessing.connection.Connection = pipe

    def writable(self) -> bool:
        return self.__pipe__.writable

    def flush(self, ignore_invalid: bool = False) -> Stream:
        if len(self) == 0:
            return self

        self.__pipe__.send(self.read())
        return self

    def write(self, __object: typing.Any, *, ignore_invalid=False) -> Stream.ListStream:
        super().write(__object, ignore_invalid=ignore_invalid)
        self.flush(ignore_invalid)
        return self

    @property
    def closed(self) -> bool:
        return self.__pipe__.closed


def spawn_subserver(event: threading.Event, host: str, route_name: str, executable_path: str, subport: int, stdout: multiprocessing.connection.Connection, stderr: multiprocessing.connection.Connection) -> None:
    try:
        root: str = os.path.abspath(os.path.dirname(__file__))
        excluded_imports: list[str] = Stream.LinqStream(sys.path).filter(lambda path: path.startswith(root)).collect(list)
        Stream.LinqStream(excluded_imports).for_each(sys.path.remove)
        closed_modules: list[str] = []

        for module_name, module in sys.modules.items():
            path: str = module.__file__ if hasattr(module, '__file__') else module.__path__ if hasattr(module, '__path__') else None

            if path is not None and path.startswith(root):
                closed_modules.append(module_name)

        for closed in closed_modules:
            del sys.modules[closed]

        executable_dir: str = os.path.dirname(executable_path)
        os.chdir(executable_dir)
        module_name: str = f'subserver-{route_name}'
        sys.path.append(executable_dir)
        spec: importlib.machinery.ModuleSpec = importlib.util.spec_from_file_location(module_name, executable_path)
        module: types.ModuleType = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        app: flask.Flask | Connection.FlaskSocketioServer | None = None
        caller: typing.Callable[[str, int], None] | None = None
        use_gevent: bool = Stream.LinqStream(vars(module).keys()).filter(lambda m: 'gevent' in m).any()

        for vname, var in vars(module).items():
            if isinstance(var, flask.Flask):
                app: flask.Flask = var
                routing: tuple[werkzeug.routing.Rule, ...] = tuple(app.url_map.iter_rules())
                callbacks: dict[str, typing.Callable] = {ep: view for ep, view in app.view_functions.items()}
                app.__init__(app.import_name, f'/proxyhost/{route_name}/{app.static_url_path.lstrip('/')}', app.static_folder, subdomain_matching=app.subdomain_matching, template_folder=app.template_folder, instance_path=app.instance_path)

                for rule in routing:
                    app.add_url_rule(rule.rule, rule.endpoint, callbacks.get(rule.endpoint) if rule.endpoint != 'static' else None, methods=rule.methods)

                caller = app.run
            elif isinstance(var, Connection.FlaskSocketioServer):
                app: Connection.FlaskSocketioServer = var
                routing: tuple[werkzeug.routing.Rule, ...] = tuple(app.app.url_map.iter_rules())
                callbacks: dict[str, typing.Callable] = {ep: view for ep, view in app.app.view_functions.items()}
                app.app.__init__(app.app.import_name, f'/proxyhost/{route_name}/{app.app.static_url_path.lstrip('/')}', app.app.static_folder, subdomain_matching=app.app.subdomain_matching, template_folder=app.app.template_folder, instance_path=app.app.instance_path)

                for rule in routing:
                    app.app.add_url_rule(rule.rule, rule.endpoint, callbacks.get(rule.endpoint) if rule.endpoint != 'static' else None, methods=rule.methods)

                caller = app.listen
            elif vname == 'main' and callable(var) and app is not None:
                caller = var

        if app is None or caller is None:
            print(f'\033[38;2;255;50;50m ... [*] [{os.getpid()}] - No server instance found!\033[0m')
            event.set()
        elif caller is not None and caller.__name__ == 'main':
            print(f'\033[38;2;50;50;255m ... [*] [{os.getpid()}] - Main handler sub-server started! --> {host}:{subport}\033[0m')
            event.set()
            sys.stdout = SubserverConsoleWriter(stdout)
            sys.stderr = SubserverConsoleWriter(stderr)
            caller(host, subport)
        elif use_gevent and isinstance(app, flask.Flask):
            print(f'\033[38;2;50;50;255m ... [*] [{os.getpid()}] - WSGI Sub-server started! --> {host}:{subport}\033[0m')
            event.set()
            sys.stdout = SubserverConsoleWriter(stdout)
            sys.stderr = SubserverConsoleWriter(stderr)
            http_server: gevent.pywsgi.WSGIServer = gevent.pywsgi.WSGIServer((host, subport), app)
            http_server.serve_forever()
        else:
            print(f'\033[38;2;50;50;255m ... [*] [{os.getpid()}] - Sub-server started! --> {host}:{subport}\033[0m')
            event.set()
            sys.stdout = SubserverConsoleWriter(stdout)
            sys.stderr = SubserverConsoleWriter(stderr)
            caller(host, subport)
    except Exception as e:
        print(f'\033[38;2;255;50;50m ... [!] [{os.getpid()}] - Error occurred whilst starting subserver!\n ... ...\n{''.join(f' ... {line}' for line in traceback.format_exception(type(e), e, e.__traceback__))}\033[0m')
        event.set()
