import server
import asyncio


routes = {}

server_instance = server.PicoTCPServer(("127.0.0.1", 8000), server.PicoHTTPRequestHandler)

app = server.RoutesHandler()


@app.create_custom_endpoint(endpoint_method="GET", endpoint_url="return100", routes=routes)
def function():
    print("100")


print(routes)


asyncio.run(server_instance.serve_forever())
