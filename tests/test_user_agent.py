"""The toolkit identifies itself in the User-Agent of clients it creates."""

from __future__ import annotations

from pytest_httpx import HTTPXMock

from glean.agent_toolkit import GleanContext, __version__
from glean.agent_toolkit.tools import search
from glean.api_client import Glean

SEARCH_URL = "https://test-instance-be.glean.com/rest/api/v1/search"
TOOLKIT_UA = f"glean-agent-toolkit/{__version__}"


def _search_response(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url=SEARCH_URL, json={"results": []})


def test_toolkit_created_client_sends_toolkit_user_agent(httpx_mock: HTTPXMock) -> None:
    """Requests from a toolkit-created client carry the toolkit's product token."""
    _search_response(httpx_mock)

    result = search(GleanContext(), query="anything")

    assert result["status"] == "ok", result
    user_agent = httpx_mock.get_requests()[0].headers["user-agent"]
    assert TOOLKIT_UA in user_agent
    # The SDK's own product token is preserved.
    assert "speakeasy-sdk" in user_agent


def test_user_agent_is_tagged_once_per_client() -> None:
    """Fetching the cached client repeatedly does not duplicate the token."""
    ctx = GleanContext()
    ctx.get_client()
    user_agent = ctx.get_client().sdk_configuration.user_agent
    assert user_agent.count(TOOLKIT_UA) == 1


def test_user_supplied_client_is_left_untouched() -> None:
    """A client the caller built keeps exactly the User-Agent they configured."""
    client = Glean(api_token="token", server_url="https://test-instance-be.glean.com")
    original = client.sdk_configuration.user_agent

    GleanContext(client=client).get_client()

    assert client.sdk_configuration.user_agent == original
