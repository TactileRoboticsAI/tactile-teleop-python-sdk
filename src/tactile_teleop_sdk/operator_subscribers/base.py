from abc import ABC, abstractmethod
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from urllib.parse import urlparse

from huggingface_hub import HfApi, login
from huggingface_hub.errors import GatedRepoError, RepositoryNotFoundError

from tactile_teleop_sdk.subscriber_node.base import create_subscriber
from tactile_teleop_sdk.protocol_auth import BaseProtocolAuthConfig
from tactile_teleop_sdk.subscriber_node.base import BaseSubscriberNode


logger = logging.getLogger(__name__)


class BaseOperatorData:
    action: str
    data: Dict[str, str]


class BaseOperatorSubscriber(ABC):
    def __init__(
        self,
        protocol_auth_config: BaseProtocolAuthConfig,
        node_id: Optional[str] = None,
        subscribe_sources: List[str] = [],
    ):
        """Initialize dataset provider"""

        self._protocol_auth_config = protocol_auth_config
        self._node_id = node_id or self.__class__.__name__
        self._subscribe_sources = subscribe_sources
        self._subscriber: Optional[BaseSubscriberNode] = None
        self._connected = False

    async def _handle_incoming_data(self, data: dict) -> None:
        """Handle incoming data from transport layer.

        Template method for protocol-specific data parsing and processing.
        Should parse the data and call add_operator_data_to_queue() to queue goals.

        Args:
            data: Raw data received from subscriber node
        """
        url = data["url"]
        message = data["message"]
        action = data["action"]
        if action == "upload":
            await upload_dataset(url, message)

    async def connect(self) -> None:
        """Connect to transport layer and start receiving data."""
        if self._connected:
            logger.warning(f"({self._node_id}) Already connected to transport layer")
            return

        self._subscriber = create_subscriber(
            node_id=self._node_id,
            subscribe_sources=self._subscribe_sources,
            protocol_auth_config=self._protocol_auth_config,
        )

        self._subscriber.register_data_callback(self._handle_incoming_data)
        await self._subscriber.connect()
        self._connected = True
        logger.info(f"({self._node_id}) ✅ Connected to transport layer and ready")

    async def disconnect(self) -> None:
        """Disconnect from transport layer."""
        if not self._connected or self._subscriber is None:
            return

        await self._subscriber.disconnect()
        self._subscriber = None
        self._connected = False
        logger.info(f"({self._node_id}) 🏁 Disconnected from transport layer")


_OPERATOR_SUBSCRIBER_REGISTRY: Dict[str, Type[BaseOperatorSubscriber]] = {}


def register_operator_subscriber(operator_name: str):
    """Decorator to register operator subscriber implementations"""

    def decorator(cls: Type[BaseOperatorSubscriber]):
        _OPERATOR_SUBSCRIBER_REGISTRY[operator_name] = cls
        return cls

    return decorator


def create_operator_subscriber(
    operator_name: str,
    protocol_auth_config: BaseProtocolAuthConfig,
    node_id: Optional[str] = None,
    subscribe_sources: List[str] = [],
) -> BaseOperatorSubscriber:
    """Factory function to create operator subscriber instance by name"""
    subscriber_cls = _OPERATOR_SUBSCRIBER_REGISTRY.get(operator_name)
    if not subscriber_cls:
        raise ValueError(
            f"Unknown operator subscriber: {operator_name}. " f"Available: {list(_OPERATOR_SUBSCRIBER_REGISTRY.keys())}"
        )
    return subscriber_cls(protocol_auth_config, node_id, subscribe_sources)


def get_repo_id(url: str):
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    path_parts = path.split("/")
    repo_id = f"{path_parts[0]}/{path_parts[1]}"
    return repo_id


async def upload_dataset(url: str, message: Optional[str] = None):
    """Upload an episode to Hugging Face Hub
    Args:
        dataset_path: Path to the dataset directory
        repo_id: Repository ID on Hugging Face Hub
        private: Whether the repository should be private
        commit_message: Custom commit message for the upload
    Returns:
        True if the upload was successful
        False otherwise
    """
    try:
        token = os.getenv("HF_TOKEN")
        datapath = os.getenv("DATASET")
        path = Path(datapath)

        if not token:
            raise ValueError("no Hugging Face token provided.")

        login(token=token)

        api = HfApi()
        repo_id = get_repo_id(url)

        api.auth_check(repo_id)

        if not message:
            message = f"Upload LeRobot dataset: {url}"

        api.upload_folder(folder_path=path, repo_id=repo_id, repo_type="dataset", commit_message=message)

        logging.info(f"Successfully uploaded episode to: https://huggingsface.co/datasets/{repo_id}")

    except RepositoryNotFoundError | GatedRepoError as e:
        raise ValueError(f"repo at {url} does either not exist or you do not have access to it: {str(e)}")
    except ValueError as e:
        raise e
