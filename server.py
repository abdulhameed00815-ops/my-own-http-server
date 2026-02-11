import socket
import sys
import json
import os
import io
import logging
from http import HTTPStatus


logger = logging.getLogger(__name__)


class PicoHTTPRequestHandler():
    def __init__(
        self,
        request_stream: io.BufferedIOBase,
        response_stream: io.BufferedIOBase,
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
        self.parser()
        self.is_dynamic_request = False
        self.server_response = b''
        if self.request_classifier():
            self.handle()


    def parser(self) -> None:
        self._parse_request()


    def _parse_request(self):
        logger.info("Parsing request line")
        requestline = self.request_stream.readline().decode()
        requestline = requestline.rstrip("\r\n")
        logger.info(requestline)

        self.command = requestline.split(' ')[0]
        self.path = requestline.split(' ')[1]

        line = self.request_stream.readline().decode()
        while line not in ('\r\n', '\n', '\r', ''):
            #now we split the line only on the first instance of ': '.
            key, value = line.rstrip('\r\n').split(': ', 1)
            self.request_headers[key] = value
            line = self.request_stream.readline().decode()
        logger.info(self.request_headers)

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

        logger.info(self.request_body)


    def request_classifier(self) -> None:
        if not self._classify_request():
            return self._return_404()
        else:
            self.handle()

    def _classify_request(self) -> bool:
        #the line below joins the current working directory (where the server runs) and the absolute path of the request.
        self.path = os.path.join(os.getcwd(), self.path.lstrip('/'))
        if os.path.isdir(self.path):
            self.path = os.path.join(self.path, 'index.html')
        elif os.path.isfile(self.path):
            pass

        if not os.path.exists(self.path):
            self.is_dynamic_request = True

        return True


    def _return_404(self) -> None:
        self.write_response_line(404)
        self.write_headers()
        self.response_stream.flush()


    def _return_405(self) -> None:
        self.write_response_line(405)
        self.write_headers()
        self.response_stream.flush()
    

    def _return_403(self) -> None:
        self.write_response_line(403)
        self.write_headers()
        self.response_stream.flush()


    def handle(self) -> None:
        self.handler()


    def handler(self) -> None:
        command = getattr(self, f'handle_{self.command}')
        command()


    def handle_GET(self) -> None:
        if not self.is_dynamic_request:
            self.handle_HEAD()
            with open(self.path, 'rb') as f:
                body = f.read()

            self.response_stream.write(body)
            self.response_stream.flush()
        else:
            server_response = b'this is a generic response from the server'
            self.server_response = server_response
            self.handle_HEAD()
            self.response_stream.write(self.server_response)
            self.response_stream.flush()
                

    def handle_POST(self) -> None:
        server_response = f'{self.request_body}'.encode("utf-8")
        self.server_response = server_response
        content_length = sys.getsizeof(self.server_response)
        self._write_response_line(200)
        self._write_headers(
                **{
                    "Content-Type": self.request_headers.get("Content-Type"),
                    "Content-Length": content_length
                }
        )
        self.response_stream.write(self.server_response)
        self.response_stream.flush()


    def handle_HEAD(self) -> None:
        self._write_response_line(200)

        if not self.is_dynamic_request:
            self._write_headers(
                    **{
                        "Content-Length": os.path.getsize(self.path)
                    }
            )
            self.response_stream.flush()
        else:
            content_length = sys.getsizeof(self.server_response)
            self._write_headers(
                    **{
                        "Content-Length": content_length
                    }
            )
            self.response_stream.flush()
            


    def _write_response_line(self, status_code: int) -> None:
        response_line = f'HTTP/1.1 {status_code} {HTTPStatus(status_code).phrase} \r\n'
        logger.info(response_line.encode())
        self.response_stream.write(response_line.encode())


    def _write_headers(self, *args, **kwargs) -> None:
        headers_copy = self.headers.copy()
        headers_copy.update(**kwargs)
        header_lines = '\r\n'.join(
                f'{k}: {v}' for k, v in headers_copy.items()
        )
        logger.info(header_lines.encode())
        self.response_stream.write(header_lines.encode())
        self.response_stream.write(b'\r\n\r\n')

        



class PicoTCPServer:
    def __init__(
            self,
            socket_address: tuple[str, int],
            request_handler: PicoHTTPRequestHandler
    ) -> None:
        self.request_handler = request_handler
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #the line below just enables us to restart the server with the same address without getting address already in use error.
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(socket_address)

        self.sock.listen()
    def serve_forever(self) -> None:
        while True:
            conn, addr = self.sock.accept()

            with conn:
                logger.info(f"Accepted connection from {addr}")
                request_stream = conn.makefile("rb")
                response_stream = conn.makefile("wb")
                self.request_handler(
                        request_stream=request_stream,
                        response_stream=response_stream
                )
                logger.info(f'Closed connection from {addr}')
                

    def __enter__(self):
        return self


    def __exit__(self, *args) -> None:
        self.sock.close()


server = PicoTCPServer(("127.0.0.1", 8000), PicoHTTPRequestHandler)
server.serve_forever()
