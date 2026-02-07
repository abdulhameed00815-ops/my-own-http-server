class PicoTCPServer:
    def __init__(
            self,
            socket_address: tuple[str, int],
            request_handler: PicoHTTPRequestHandler
    ) -> None:
        self.request_handler = request_handler
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(socket_adress)

        self.sock.listen()
    def serve_forever(self) -> None:
        while True:
            conn, addr = self.socket.accept()

            with conn:
                log.info(f"Accepted connection from {addr}")
                request_stream = conn.makefile("rb")
                response_stream = conn.makefile("wb")
                self.request_handler(
                        request_stream=request_stream,
                        response_stream=response_stream
                )
