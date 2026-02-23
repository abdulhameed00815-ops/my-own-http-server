from server import PicoHTTPRequestHandler, PicoTCPServer, RoutesHandler
import asyncio


app = RoutesHandler()


@app.create_custom_endpoint(endpoint_method="GET", endpoint_url="multiply/{x}/{y}")
def function(x: int, y: int):
    return x * y


routes = app.routes

server_instance = PicoTCPServer(routes=routes, request_handler=PicoHTTPRequestHandler, socket_address=("127.0.0.1", 8000))

asyncio.run(server_instance.serve_forever())
