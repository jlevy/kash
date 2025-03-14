import socket
import time
from collections.abc import Iterable

from kash.config.logger import get_logger

log = get_logger(__name__)


def local_port_is_free(host: str, port: int) -> bool:
    """
    Check if the specified port is free.

    Returns True if the port is free, False otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def wait_for_local_port(host: str, port: int, timeout: int = 0):
    """
    Check if the specified port is free. Will log a warning if the port is in
    use and wait until it becomes available.
    """
    start_time = time.time()
    errors = 0
    while True:
        if local_port_is_free(host, port):
            if errors > 0:
                log.message("Port %s:%s is free again!", host, port)
            return
        else:
            elapsed_time = time.time() - start_time
            if timeout and elapsed_time > timeout:
                log.error(
                    "Port %s:%s still in use after %s seconds. Giving up.",
                    host,
                    port,
                    timeout,
                )
                raise RuntimeError("Port in use")
            if errors == 0:
                log.warning(
                    "Cannot bind to %s:%s. Will wait for port to become free.",
                    host,
                    port,
                )
            errors += 1
            time.sleep(2)


def find_available_local_port(host: str, ports: Iterable[int]) -> int:
    """
    Find the first available port from an iterable of port numbers.
    Returns the first port that is free.

    Raises RuntimeError if none of the ports are available.
    """
    for port in ports:
        if local_port_is_free(host, port):
            log.info("Found available port: %s:%s", host, port)
            return port
    raise RuntimeError("No available ports found.")
