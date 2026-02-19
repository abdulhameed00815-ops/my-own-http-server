from server import PicoTCPServer, PicoHTTPRequestHandler
import asyncio


app = PicoTCPServer(("127.0.0.1", 8000), PicoHTTPRequestHandler)

@app.create_custom_endpoint(endpoint_method="GET", endpoint_url="return100")
def function():
    print("100")


asyncio.run(app.serve_forever())
