import socket
import os


class PicoHTTPRequestHandler():
    def __init__(
        self,
        request_stream: io.BufferedIOBase,
        response_stream: io.BufferedIOBase,
    ):
        self.request_stream = request_stream
        self.client = client
        self.command = ''
        self.path = ''
        self.headers = {
                'Content-Type:': 'text/html',
                'Content-Length': '0',
                'Connection': 'close'
        }
        self.data = ''
        self.handle()


    def handle(self) -> None:
        self._parse_request()


    def _parse_request(self):
        logger.info("Parsing request line")
        requestline = self.request_stream.readline().decode()
        requestline = requestline.rstrip("\r\n")
        logger.info(requestline)

        self.command = requestline.split(' ')[0]
        self.path = requestline.split(' ')[1]

        headers = {}
        line = self.request_stream.readline().decode()
        while line not in ('\r\n', '\n', '\r', ''):
            header = line.rstrip('\r\n').split(': ')
            headers[header[0]] = header[1]
            line = self.request_stream.readline().decode()
        logger.info(headers)


    def handle_GET(self) -> None:
        pass


    def handle_HEAD(self) -> None:
        pass

        
class PicoHTTPHandler:
    def handler(self) -> None:
        self._parse_request():

        if not self._validate_path():
            return self._return_404()

        if self.command == "POST":
            return self._return_403()

        if self.command not in ("HEAD", "GET"):
            return self._return_405()
    

    def _validate_path(self) -> bool:
        #the line below joins the current working directory (where the server runs) and the absolute path of the request.
        self.path = os.path.join(os.getcwd(), self.path.lstrip('/'))
        if os.path.isdir(self.path):
            self.path = os.path.join(self.path, 'index.html')
        elif os.path.isfile(self.path):
            pass

        if not os.path.exists(self.path):
            return False

        return True


    def _return_404(self) -> None:
        self.write_response_line(404)
        self.write_headers()


    def _return_405(self) -> None:
        self.write_response_line(405)
        self.write_headers()
    

    def _return_403(self) -> None:
        self.write_response_line(403)
        self.write_headers()



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
                

    def __enter__(self) -> PicoTCPServer:
        return self


    def __exit__(self, *args) -> None:
        self.sock.close()



