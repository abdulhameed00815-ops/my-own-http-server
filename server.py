type Scope = MutableMapping[str, Any]
type Message = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[Message]]
type Send = Callable[[Message], Awaitable[None]]


async def handle_lifespan(scope: Scope, receive: Receive, send: Send):
    assert scope["type"] == "lifespan"
    while True:
        message = await recieve()
        print(f"Got message:", message)


total_connections = 0


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
            use_colors=False,
    )


if __name__ == "__main__":
    main()
