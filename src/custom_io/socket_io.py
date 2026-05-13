import random
import socket


def is_port_free(
    port: int, host: str = "127.0.0.1"
) -> bool:
    with socket.socket(
        socket.AF_INET, socket.SOCK_STREAM
    ) as sock:
        return sock.connect_ex((host, port)) != 0


def choose_free_port(
    start: int = 50052,
    end: int = 50152,
    attempts: int = 20,
) -> int:
    ports = random.sample(
        range(start, end + 1),
        k=min(attempts, end - start + 1),
    )

    for port in ports:
        if is_port_free(port):
            return port

    raise RuntimeError(
        f"No free port found in range {start}-{end}"
    )
