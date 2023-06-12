<!-- PROJECT LOGO -->
<br />
<p align="center">
  <img src="images/logo.png" alt="Logo" width=100>
<p>
<h2 align="center">WG-Discord</h2>

<!-- TABLE OF CONTENTS -->
### Table of Contents

- [About](#about)
  - [Built With](#built-with)
- [Deployment](#deployment)
  - [Configuration](#configuration)
  - [Python](#python)
  - [Docker-Compose](#docker-compose)

## About

WG-Discord is an admin and user-friendly tool for deploying a Discord-integrated WireGuard instance. The application will instantiate WireGuard, process user keys, and assign IP addresses.

### Built With

3rd-Party Packages:

- [wgconfig](https://github.com/towalink/wgconfig) - WireGuard config parsing
- [Hikari](https://github.com/hikari-py/hikari) - Discord API library
- [Lightbulb](https://github.com/tandemdude/hikari-lightbulb) - Command handler for Hikari
- [Pydantic](https://github.com/pydantic/pydantic) - Used for app configuration management

## Deployment

**IMPORTANT:** WireGuard requires **root** access to run so that it can modify network interfaces and routing. For this reason, there are a couple ways to execute WG-Discord:

- Called directly as a python package on host
- Spun up via Docker-Compose

**Mitigation:** In order to limit potential system vulnerability, the Docker deployment will run as root in a container with host network access and NET_ADMIN activated. This configuration provides a reduced surface, and improved security over running the Python package directly on the host.

### Configuration

**Required**  
The following are configuration items must be set to properly start:
| Name | WG Mapping | Description |
| --- | --- | --- |
| BOT_TOKEN |  | Your bot's Discord token |
| WIREGUARD_CONFIG_PATH |  | File path for WireGuard config file (ex. `/etc/wireguard/wg0.conf`) |
| WIREGUARD_USER_CONFIG_DIR |  | Directory path for storing user configurations (ex. `/etc/wireguard/`) |
| GUILD_PRIVATE_KEY | PrivateKey | WireGuard private key to be used on the application interface |
| GUILD_IP_INTERFACE | Address | CIDR address that defines both the app's IP and IP range assignable to users |
| GUILD_INTERFACE_LISTEN_PORT | ListenPort | Port that WireGuard will listen on |
| USER_ENDPOINT | Endpoint | Address or hostname and port that users will connect to |
| USER_ALLOWED_IPS | AllowedIPs | IP ranges the user will have routed through WireGuard |

**Optional**  
The following are not needed but may be applicable for your WireGuard needs:
| Name | WG Mapping | Description |
| --- | --- | --- |
| GUILD_INTERFACE_RESERVED_NETWORK_ADDRESSES |  | IP addresses not available for auto-assignment |
| ~~GUILD_INTERFACE_DNS~~ | ~~DNS~~ | ~~Comma-separated list of IP addresses or non-IP hostnames~~ |
| ~~GUILD_INTERFACE_TABLE~~ | ~~Table~~ | ~~Routing table to which routes are added~~ |
| ~~GUILD_INTERFACE_MTU~~ | ~~MTU~~ | ~~MTU to override automatic discovery~~ |
| GUILD_PRE_UP | PreUp | Command to be run before the interface starts |
| GUILD_POST_UP | PostUp | Command to be run after the interface starts |
| GUILD_PRE_DOWN | PreDown | Command to be run before the interface stops |
| GUILD_POST_DOWN | PostDown | Command to be run after the interface stops |
| ~~USER_PERSISTENT_KEEP_ALIVE~~ | ~~PersistentKeepalive~~ | ~~Time (seconds) interval to send keepalive packet to the server endpoint~~ |

### Python

**Dependencies**  
The following are required to be on the host:

```text
Python >= 3.11
WireGuard (incl. wg-quick)
```

1. Run package

    ```text
    python -m wg-discord
    ```

### Docker-Compose

**NOTE:** The Docker-Compose instance does not require WireGuard to be installed on the host, and will store its WireGuard config file via Docker Volume.

1. Build:

    ```text
    make build
    ```

1. Run:

    ```text
    make up
    ```

1. Verify:

    ```text
    make logs
    ```
