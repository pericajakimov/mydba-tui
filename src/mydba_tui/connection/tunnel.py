"""
SSH tunnel management using paramiko.

Establishes SSH tunnels for connecting to MySQL servers through
jump hosts. Uses paramiko's transport and channel forwarding
to map a local port to the remote MySQL port.
"""

import socket
import threading
from pathlib import Path

import paramiko

from mydba_tui.models.profile import Profile, SshTunnelConfig


class SshTunnel:
    """SSH tunnel that forwards a local port to a remote MySQL server.

    Usage:
        tunnel = SshTunnel(ssh_config, remote_host, remote_port)
        tunnel.start()
        # Connect MySQL to 127.0.0.1:tunnel.local_port
        tunnel.stop()
    """

    def __init__(self, ssh_config: SshTunnelConfig, remote_host: str, remote_port: int) -> None:
        """Initialize the tunnel.

        Args:
            ssh_config: SSH connection parameters.
            remote_host: MySQL host (as seen from the SSH server).
            remote_port: MySQL port.
        """
        self._ssh_config = ssh_config
        self._remote_host = remote_host
        self._remote_port = remote_port
        self._transport: paramiko.Transport | None = None
        self._server_socket: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._forward_threads: list[threading.Thread] = []
        self._running = False
        self.local_port: int = 0

    def start(self) -> None:
        """Establish the SSH connection and start port forwarding.

        Raises:
            Exception: If SSH connection fails.
        """
        ssh = self._ssh_config

        # Create SSH transport
        sock = socket.create_connection((ssh.host, ssh.port), timeout=10)
        self._transport = paramiko.Transport(sock)

        # Authenticate
        if ssh.key_file:
            key_path = Path(ssh.key_file).expanduser()
            if key_path.exists():
                pkey = paramiko.RSAKey.from_private_key_file(str(key_path))
                self._transport.connect(username=ssh.username, pkey=pkey)
            elif ssh.password:
                self._transport.connect(username=ssh.username, password=ssh.password)
            else:
                self._transport.connect(username=ssh.username)
        elif ssh.password:
            self._transport.connect(username=ssh.username, password=ssh.password)
        else:
            # Try SSH agent for key-based auth
            self._transport.connect(username=ssh.username)

        # Bind a local socket for the tunnel
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(("127.0.0.1", 0))
        self._server_socket.settimeout(1.0)
        self.local_port = self._server_socket.getsockname()[1]
        self._server_socket.listen(5)

        # Start accepting connections in a thread
        self._running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

        # Brief wait to ensure the accept loop is ready
        import time

        time.sleep(0.2)

    def stop(self) -> None:
        """Stop the tunnel and clean up resources."""
        self._running = False

        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except Exception:
                pass

        if self._transport is not None:
            try:
                self._transport.close()
            except Exception:
                pass

    def _accept_loop(self) -> None:
        """Accept local connections and forward them through the SSH channel."""
        while self._running:
            try:
                client_socket, _ = self._server_socket.accept()  # type: ignore[union-attr]
            except TimeoutError:
                continue
            except OSError:
                break

            # Open a channel to the remote host through the SSH transport
            try:
                channel = self._transport.open_channel(  # type: ignore[union-attr]
                    "direct-tcpip",
                    (self._remote_host, self._remote_port),
                    client_socket.getpeername(),
                    timeout=10,
                )
            except Exception:
                client_socket.close()
                continue

            if channel is None:
                client_socket.close()
                continue

            # Forward data between local socket and SSH channel
            thread = threading.Thread(
                target=self._forward_data, args=(client_socket, channel), daemon=True
            )
            thread.start()
            self._forward_threads.append(thread)

    @staticmethod
    def _forward_data(local_socket: socket.socket, channel: paramiko.Channel) -> None:
        """Bidirectionally forward data between local socket and SSH channel."""
        import select

        while True:
            try:
                readable, _, _ = select.select([local_socket, channel], [], [], 1.0)
            except Exception:
                break

            if local_socket in readable:
                data = local_socket.recv(4096)
                if not data:
                    break
                channel.sendall(data)

            if channel in readable:
                data = channel.recv(4096)
                if not data:
                    break
                local_socket.sendall(data)

        local_socket.close()
        channel.close()


def create_tunnel(profile: Profile) -> SshTunnel | None:
    """Create an SSH tunnel based on profile configuration.

    If the profile has no SSH tunnel configuration, returns None.
    Otherwise creates the tunnel (not yet started).

    Args:
        profile: Connection profile with optional SSH tunnel config.

    Returns:
        SshTunnel instance (not yet started), or None.
    """
    if profile.ssh_tunnel is None or not profile.ssh_tunnel.host:
        return None

    return SshTunnel(profile.ssh_tunnel, profile.host, profile.port)
