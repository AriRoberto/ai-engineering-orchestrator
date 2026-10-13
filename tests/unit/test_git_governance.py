import pytest

from ai_engineering.governance.git import GitGovernanceService, GitOperation, GovernanceViolation


@pytest.mark.parametrize("branch", ["main", "master", "develop"])
def test_protected_branches_reject_writes(branch: str) -> None:
    with pytest.raises(GovernanceViolation):
        GitGovernanceService().authorize(GitOperation.WRITE, branch, approved=True)


def test_agent_branch_requires_approval_then_allows_write() -> None:
    service = GitGovernanceService()
    branch = service.create_branch_name("software-engineer", "feat", "dashboard", "001")
    pending = service.authorize(GitOperation.WRITE, branch)
    assert not pending.allowed and pending.requires_human_approval
    assert service.authorize(GitOperation.WRITE, branch, approved=True).allowed


@pytest.mark.parametrize("operation", [GitOperation.FORCE_PUSH, GitOperation.MERGE])
def test_automated_destructive_operations_are_forbidden(operation: GitOperation) -> None:
    with pytest.raises(GovernanceViolation):
        GitGovernanceService().authorize(operation, "agents/devops/fix-pipeline-003", approved=True)
