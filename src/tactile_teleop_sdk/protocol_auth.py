from typing import Dict, Type
from pydantic import BaseModel


class BaseProtocolAuthConfig(BaseModel):
    """Base configuration for protocol authentication and connection"""
    protocol: str
    room_name: str
    token: str
    server_url: str


_PROTOCOL_AUTH_CONFIG_REGISTRY: Dict[str, Type[BaseProtocolAuthConfig]] = {}


def register_protocol_auth_config(protocol_name: str):
    """Decorator to register protocol auth config"""
    def decorator(cls: Type[BaseProtocolAuthConfig]):
        _PROTOCOL_AUTH_CONFIG_REGISTRY[protocol_name] = cls
        return cls
    return decorator


def create_protocol_auth_config(
    protocol: str,
    room_name: str,
    token: str,
    server_url: str,
    **kwargs
) -> BaseProtocolAuthConfig:
    """Factory to create protocol-specific auth config"""
    config_cls = _PROTOCOL_AUTH_CONFIG_REGISTRY.get(protocol)
    if not config_cls:
        raise ValueError(
            f"Unknown protocol: {protocol}. "
            f"Available: {list(_PROTOCOL_AUTH_CONFIG_REGISTRY.keys())}"
        )
    return config_cls(
        protocol=protocol,
        room_name=room_name,
        token=token,
        server_url=server_url,
        **kwargs
    )

