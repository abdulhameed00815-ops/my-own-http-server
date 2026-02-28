from server import PicoHTTPRequestHandler, PicoTCPServer, RoutesHandler
from pydantic import BaseModel, ValidationError
import asyncio


app = RoutesHandler()


class User(BaseModel):
    name:str
    password:str


@app.create_custom_endpoint(endpoint_method="POST", endpoint_url="login")
def login(user: User):
    message = f"{user.name}'s logged in successfuly!"
    return message


@app.create_custom_endpoint(endpoint_method="GET", endpoint_url="divide/{x}/{y}")
def divide(x: int, y: int):
    return x / y


routes = app.routes

server_instance = PicoTCPServer(routes=routes, request_handler=PicoHTTPRequestHandler, socket_address=("127.0.0.1", 8000))

asyncio.run(server_instance.serve_forever())
