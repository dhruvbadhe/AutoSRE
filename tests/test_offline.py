import socket

import pytest


def test_real_network_is_blocked():
    with pytest.raises(RuntimeError, match="Network access attempted"):
        socket.create_connection(("93.184.216.34", 443), timeout=1)
