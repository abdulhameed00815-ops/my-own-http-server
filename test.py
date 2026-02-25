from server import PicoHTTPRequestHandler, PicoTCPServer, RoutesHandler
import asyncio


app = RoutesHandler()


@app.create_custom_endpoint(endpoint_method="GET", endpoint_url="message/{name}/{age}")
def function(name: str, age: int):
    message = f"{name} is {age} years old"
    return message


routes = app.routes

server_instance = PicoTCPServer(routes=routes, request_handler=PicoHTTPRequestHandler, socket_address=("127.0.0.1", 8000))

asyncio.run(server_instance.serve_forever())
