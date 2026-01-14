#a bunch of dictionaries to map some types.
type Scope = MutableMapping[str, Any]
type Message = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[Message]]
type Send = Callable[[Message], Awaitable[None]]


people = [
    {
        "name": "lauren",       
        "age": "23"
    },
    {
        "name": "basmallah",
        "age": "19"
    }
]


#function to handle the beginning of the lifespan of the app.
async def handle_lifespan(scope: Scope, receive: Receive, send: Send):
    assert scope["type"] == "lifespan"
    while True:
        message = await receive()
        print(f"Got message:", message)
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})        
            break


async def getage_endpoint(scope: Scope, receive: Receive, send: Send):
    for person in people:
        if scope["path"].endswith(person["name"]):
            response_message = {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
            print("Sending response start:", response_message)
            await send(response_message)
            person_age = f"{person['age']}"
            encoded_age = person_age.encode("utf-8")
            response_message = {
                "type": "http.response.body",
                "body": encoded_age,
                "more_body": False,
            }   
            print("Sending response body:", response_message)
            await send(response_message)


async def error_endpoint(scope: Scope, receive: Receive, send: Send):
    response_message = {
        "type": "http.response.start",
        "status": 400,
        "headers": [(b"content-type", b"text/plain")],
    }
    print("Sending response start:", response_message)
    await send(response_message)
    response_message = {
        "type": "http.response.body",
        "body": b'no route or incorrect route!',
        "more_body": False,
    }
    print("Sending response body:", response_message)
    await send(response_message)
    

async def handle_http(scope: Scope, receive: Receive, send: Send):
    assert scope["type"] == "http"

    if scope["path"].startswith("/getage") and scope["method"] == "GET":
        await getage_endpoint(scope, receive, send)
    else:
        await error_endpoint(scope, receive, send)


total_connections = 0


#the main app, all requests (http/lifespan) are handled here.
async def app(scope: Scope, receive: Receive, send: Send) -> None:
    global total_connections
    total_connections += 1
    current_connection = total_connections
    print(f"Beginning connection {current_connection}. Scope: ", scope)
    if scope["type"] == "lifespan":
        await handle_lifespan(scope, receive, send)
    elif scope["type"] == "http":
        await handle_http(scope, receive, send)
    print(f"Ending connection {current_connection}")


def main():
    import uvicorn

    uvicorn.run(
            app,
            port=5000,
            log_level="info",
            use_colors=True,
    )


if __name__ == "__main__":
    main()
