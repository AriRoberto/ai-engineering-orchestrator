from ai_engineering.evidence.github import UrllibGitHubTreeTransport
from ai_engineering.security.credentials import (
    FileGitHubTokenProvider,
    ScopedGitHubTokenProvider,
)


def test_token_is_returned_only_for_the_configured_repository() -> None:
    provider = ScopedGitHubTokenProvider("secret-token", "AriRoberto/app-ams")

    assert provider.token_for("AriRoberto", "app-ams") == "secret-token"
    assert provider.token_for("AriRoberto", "app-financas") is None
    assert "secret-token" not in repr(provider)


def test_transport_adds_authorization_only_inside_private_scope() -> None:
    transport = UrllibGitHubTreeTransport(
        credential_provider=ScopedGitHubTokenProvider(
            "secret-token", "AriRoberto/app-ams"
        )
    )

    private_headers = transport._headers(
        "AriRoberto", "app-ams", "application/vnd.github+json"
    )
    public_headers = transport._headers(
        "AriRoberto", "app-financas", "application/vnd.github+json"
    )

    assert private_headers["Authorization"] == "Bearer secret-token"
    assert "Authorization" not in public_headers


def test_file_provider_reads_only_for_configured_scope(tmp_path) -> None:
    token_file = tmp_path / "github-token"
    token_file.write_text("ephemeral-token\n", encoding="utf-8")
    provider = FileGitHubTokenProvider(str(token_file), "AriRoberto/app-ams")

    assert provider.token_for("AriRoberto", "app-ams") == "ephemeral-token"
    assert provider.token_for("other", "repository") is None
    assert "ephemeral-token" not in repr(provider)


def test_file_provider_fails_closed_for_missing_or_oversized_secret(tmp_path) -> None:
    missing = FileGitHubTokenProvider(str(tmp_path / "missing"), "AriRoberto/app-ams")
    oversized_file = tmp_path / "oversized"
    oversized_file.write_text("x" * 4097, encoding="utf-8")
    oversized = FileGitHubTokenProvider(str(oversized_file), "AriRoberto/app-ams")

    assert missing.token_for("AriRoberto", "app-ams") is None
    assert oversized.token_for("AriRoberto", "app-ams") is None
