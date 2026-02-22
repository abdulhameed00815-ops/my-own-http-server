from server import PicoHTTPRequestHandler, PicoTCPServer, RoutesHandler
import asyncio


routes = {}
app = RoutesHandler()


@app.create_custom_endpoint(endpoint_method="GET", endpoint_url="return100", routes=routes)
def function():
    print("100")


print(routes)

server_instance = PicoTCPServer(routes=routes, request_handler=PicoHTTPRequestHandler, socket_address=("127.0.0.1", 8000))

asyncio.run(server_instance.serve_forever())
