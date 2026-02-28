import functools
from typing import Type
from pydantic import ValidationError
import json
from pathlib import Path
import asyncio
import socket
import json
import os
import io
import logging
from http import HTTPStatus
from queue import Queue
import inspect


q = Queue(maxsize=100)


routes = {}


class RoutesHandler():
    def __init__(self):
        self.routes = {}
        self.func_sig = None


    def create_custom_endpoint(self, endpoint_method, endpoint_url):
        def decorator(func):
            p_posix = Path(endpoint_url)
            route_name = p_posix.parts[0]
            sig = inspect.signature(func)
            self.func_sig = sig
            self.routes[f"{endpoint_method}{route_name}"] = func
            self.routes[f"sig{endpoint_method}{route_name}"] = sig
            self.routes[f"paramschema{endpoint_method}{route_name}"] = endpoint_url.replace(f"{route_name}/", "")
            return func
        return decorator


class PicoHTTPRequestHandler():
    def __init__(
        self,
        request_stream: io.BufferedIOBase,
        response_stream: io.BufferedIOBase,
        routes: dict[str, callable],
    ):
        self.request_stream = request_stream
        self.response_stream = response_stream
        self.command = ''
        self.path = ''
        self.request_headers = {}
        self.headers = {
                'Content-Type': 'text/html',
                'Content-Length': '0',
                'Connection': 'close'
        }
        self.request_body = ''
        self.is_dynamic_request = False
        self.server_response = b''
        self.routes = routes
        self.route_name = ''
        self.endpoint_function = None
        self.parser()

        self.handler()
        

    def parser(self) -> None:
        self._parse_request()


    def _parse_request(self):
        requestline = self.request_stream.readline().decode()
        requestline = requestline.rstrip("\r\n")

        self.command = requestline.split(' ')[0]
        self.path = requestline.split(' ')[1]

        line = self.request_stream.readline().decode()
        while line not in ('\r\n', '\n', '\r', ''):
            #now we split the line only on the first instance of ': '.
            key, value = line.rstrip('\r\n').split(': ', 1)
            self.request_headers[key] = value
            line = self.request_stream.readline().decode()

        content_type = self.request_headers.get('Content-Type', None)

        if content_type == "text/plain" or content_type == "text/html":
            content_length = int(self.request_headers.get('Content-Length', 0))
            if content_length > 0:
                request_body = self.request_stream.read(content_length)
                self.request_body = request_body.decode()
        elif content_type == "application/json":
            content_length = int(self.request_headers.get('Content-Length', 0))
            if content_length > 0:
                body_json_string = self.request_stream.read(content_length)
                self.request_body = json.loads(body_json_string)


    def handler(self) -> None:
        command = getattr(self, f'handle_{self.command}')
        command()


    def is_static_file_request(self) -> bool:
        if not os.path.exists(self.path):
            return False

        self.path = os.path.join(os.getcwd(), self.path.lstrip('/'))
        if os.path.isdir(self.path):
            self.path = os.path.join(self.path, 'index.html')
        elif os.path.isfile(self.path):
            pass


    def _return_404(self) -> None:
        self._write_response_line(404)
        self._write_headers()
        self.response_stream.flush()


    def _return_405(self) -> None:
        self.write_response_line(405)
        self.write_headers()
        self.response_stream.flush()


    def _return_400(self) -> None:
        self.write_response_line(400)
        self.write_headers()
        self.response_stream.flush()


    def _return_403(self) -> None:
        self.write_response_line(403)
        self.write_headers()
        self.response_stream.flush()


    def handle_GET(self) -> None:
        if self.is_static_file_request():
            self.handle_HEAD()
            with open(self.path, 'rb') as f:
                body = f.read()

            self.response_stream.write(body)
            self.response_stream.flush()
        else:
            if self.endpoint_exists():
                request_params = self.inject_request_params()

                server_response = str(self.endpoint_function(*request_params)).encode("utf-8")

                self.server_response = server_response
                self.handle_HEAD()
                self.response_stream.write(self.server_response)
                self.response_stream.flush()
            else:
                self._return_404()


    def handle_POST(self) -> None:
        if not self.endpoint_exists():
            self._return_404()

        if type(self.request_body) == dict:
            if self.validate_json_body():
                class_model = self.return_class_model()
                server_response = str(self.endpoint_function(class_model)).encode("utf-8")
                self.server_response = server_response
                content_length = len(server_response)
                self._write_response_line(200)
                self._write_headers(
                        **{
                            "Content-Type": self.request_headers.get("Content-Type"),
                            "Content-Length": content_length
                        }
                )
                self.response_stream.write(self.server_response)
                self.response_stream.flush()


    def endpoint_exists(self) -> bool:
        self.path = self.path.lstrip("/")
        request_route_paths = self.path.split("/")
        request_route_name = request_route_paths[0]
        if f"{self.command}{request_route_name}" in self.routes:
            self.endpoint_function = self.routes[f"{self.command}{request_route_name}"]
            self.route_name = request_route_name
            return True
        else:
            return False


    def inject_request_params(self) -> list:
        request_path_params = self.request_path_params()

        request_params = []
        for component in request_path_params:
            request_params.append(component)  

        param_signatures = []
        sig = self.routes[f"sig{self.command}{self.route_name}"]

        for name, param in sig.parameters.items():
            parameter = {
                    "name": name,
                    "type": param.annotation,
            }
            param_signatures.append(parameter)

        paramschema = self.routes[f"paramschema{self.command}{self.route_name}"]

        paramschema_list = paramschema.split("/") 

        ordered_param_name_to_types = []

        for param in paramschema_list:
            param = param.lstrip("{").rstrip("}")
            for param_signature in param_signatures:
                if param_signature["name"] == param:
                    param_name_to_type = {
                            "name": param,
                            "type": param_signature["type"],
                    }
                    ordered_param_name_to_types.append(param_name_to_type)

        final_request_params = []

        for index, request_param in enumerate(request_params):
            target_type = ordered_param_name_to_types[index]['type']
            request_param = target_type(request_param)
            final_request_params.append(request_param)

        return final_request_params


    def request_path_params(self) -> list:
        request_params = []
        request_path = self.path.replace("/home/abdo/Documents/my-own-http-server/", "")
        components = request_path.split("/") 
        for component in components:
           if not component == self.route_name:
               request_params.append(component)
        return request_params


    def validate_json_body(self) -> bool:
        if not type(self.request_body) == dict:
            return False
        
        param_signatures = []
        sig = self.routes[f"sig{self.command}{self.route_name}"]

        for name, param in sig.parameters.items():
            parameter = {
                    "name": name,
                    "annotation": param.annotation,
            }
            param_signatures.append(parameter)

        for param_sig in param_signatures:
            if inspect.isclass(param_sig["annotation"]):
                model = param_sig["annotation"]
        
        request_body = self.request_body

        try:
            model.model_validate(request_body)
            return True
        except ValidationError:
            return False


    #this function looks for function params of type class, instantiates it with the keyword arguments of the request_body, then returns the instance of the class.
    def return_class_model(self) -> Type:
        param_signatures = []
        sig = self.routes[f'sig{self.command}{self.path.replace("/", "")}']

        for name, param in sig.parameters.items():
            parameter = {
                    "name": name,
                    "annotation": param.annotation,
            }
            param_signatures.append(parameter)

        for param_sig in param_signatures:
            if inspect.isclass(param_sig["annotation"]):
                model = param_sig["annotation"]

        return model(**self.request_body)


    def handle_HEAD(self) -> None:
        self._write_response_line(200)

        if self.is_static_file_request():
            self._write_headers(
                    **{
                        "Content-Length": len(self.path)
                    }
            )
            self.response_stream.flush()
        else:
            content_length = len(self.server_response)
            self._write_headers(
                    **{
                        "Content-Length": content_length
                    }
            )
            self.response_stream.flush()


    def _write_response_line(self, status_code: int) -> None:
        response_line = f'HTTP/1.1 {status_code} {HTTPStatus(status_code).phrase} \r\n'
        self.response_stream.write(response_line.encode())


    def _write_headers(self, *args, **kwargs) -> None:
        headers_copy = self.headers.copy()
        headers_copy.update(**kwargs)
        header_lines = '\r\n'.join(
                f'{k}: {v}' for k, v in headers_copy.items()
        )
        self.response_stream.write(header_lines.encode())
        self.response_stream.write(b'\r\n\r\n')


class PicoTCPServer():
    def __init__(
            self,
            socket_address: tuple[str, int],
            request_handler: PicoHTTPRequestHandler,
            routes: dict[str, callable]
    ) -> None:
        self.routes = routes
        self.request_handler = request_handler
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #the line below just enables us to restart the server with the same address without getting address already in use error.
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(socket_address)

        self.sock.listen()


    async def serve_forever(self) -> None:
        while True:
            conn, addr = self.sock.accept()

            q.put((conn, addr))
            print("accepted and enqueued conn and addr")
            await self.main()


    async def main(self):
        handle_connection = asyncio.create_task(self.worker())
        await handle_connection


    async def worker(self):
        conn, addr = q.get()
        with conn:
            print(f"Accepted connection from {addr}")
            request_stream = conn.makefile("rb")
            response_stream = conn.makefile("wb")
            self.request_handler(
                    request_stream=request_stream,
                    response_stream=response_stream,
                    routes=self.routes
            )
            print(f'Closed connection from {addr}')


    def __enter__(self):
        return self


    def __exit__(self, *args) -> None:
        self.sock.close()




