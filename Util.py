import enum
import socket


class ProgramType(enum.IntEnum):
    PROGRAM = 0
    WEBSITE = 1
    GAME = 2


class ContactType(enum.IntEnum):
    NONE = 0
    URL = 1
    MAIL = 2
    PHONE = 3


class UserElevationType(enum.IntEnum):
    SUPERUSER = 0
    ADMINISTRATOR = 1
    MODERATOR = 2


def get_addr_ipv4_ipv6(ip: str) -> tuple[int, bool | None]:
    """
    Checks if the specified IP string is ipv4 or ipv6
    :param ip: (str) The IP address
    :return: (int, bool | None) The converted IP address or -1 and True if ipv6, False if ipv4, None if not an IP address
    """

    try:
        remote: int = int.from_bytes(socket.inet_aton(ip), 'little')
        return remote, False
    except socket.error:
        try:
            remote: int = int.from_bytes(socket.inet_pton(socket.AF_INET6, ip), 'little')
            return remote, True
        except socket.error:
            return -1, None


def to_functional_name(name: str) -> str:
    assert isinstance(name, str) and len(name) > 0
    result: list[str] = []
    allowed: tuple[str, ...] = tuple('abcdefghijklmnopqrstuvwxyz0123456789')

    for c in name.lower():
        result.append(c if c in allowed else '_')

    return ''.join(result)
