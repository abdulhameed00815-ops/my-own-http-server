from server import PicoHTTPRequestHandler, PicoTCPServer, RoutesHandler
from pydantic import BaseModel, ValidationError
import asyncio


app = RoutesHandler()


class User(BaseModel):
    name:str
    password:str


@app.create_custom_endpoint(endpoint_method="POST", "login")
def function(user: User):
    message = f"{user.name}'s logged in successfuly!"
    return message


routes = app.routes

server_instance = PicoTCPServer(routes=routes, request_handler=PicoHTTPRequestHandler, socket_address=("127.0.0.1", 8000))

asyncio.run(server_instance.serve_forever())
