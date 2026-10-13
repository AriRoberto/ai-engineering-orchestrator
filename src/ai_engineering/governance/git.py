import re
from dataclasses import dataclass
from enum import StrEnum


class GitOperation(StrEnum):
    READ = "read"
    WRITE = "write"
    FORCE_PUSH = "force-push"
    MERGE = "merge"


class GovernanceViolation(PermissionError):
    pass


@dataclass(frozen=True)
class GitAuthorization:
    allowed: bool
    requires_human_approval: bool
    reason: str


class GitGovernanceService:
    protected_branches = frozenset({"main", "master", "develop"})
    branch_pattern = re.compile(r"^agents/[a-z0-9-]+/[a-z0-9-]+-[a-z0-9-]+-[a-z0-9]+$")

    def authorize(
        self, operation: GitOperation, branch: str, approved: bool = False
    ) -> GitAuthorization:
        if operation in {GitOperation.FORCE_PUSH, GitOperation.MERGE}:
            raise GovernanceViolation(f"Automated {operation.value} is forbidden")
        if operation == GitOperation.WRITE and branch in self.protected_branches:
            raise GovernanceViolation(f"Direct writes to protected branch '{branch}' are forbidden")
        if operation == GitOperation.WRITE and not self.branch_pattern.fullmatch(branch):
            raise GovernanceViolation(
                "Write branch does not comply with agents/<agent>/<type>-<description>-<id>"
            )
        if operation == GitOperation.WRITE and not approved:
            return GitAuthorization(
                False, True, "Human approval required before publishing changes"
            )
        return GitAuthorization(True, False, "Operation authorized")

    def create_branch_name(
        self, agent: str, change_type: str, description: str, task_id: str
    ) -> str:
        values = [agent, change_type, description, task_id]
        if any(not re.fullmatch(r"[a-z0-9-]+", value) for value in values):
            raise ValueError("Branch components must be lowercase kebab-case")
        branch = f"agents/{agent}/{change_type}-{description}-{task_id}"
        if not self.branch_pattern.fullmatch(branch):
            raise ValueError("Invalid governed branch name")
        return branch
