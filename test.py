from server import PicoTCPServer, PicoHTTPRequestHandler
import asyncio


server = PicoTCPServer(("127.0.0.1", 8000), PicoHTTPRequestHandler)

server.create_custom_endpoint(
endpoint_method="GET", 
endpoint_url="http://127.0.0.1:8000/return100", 
endpoint_function="""
function():
    return 100
""")

asyncio.run(server.serve_forever())
