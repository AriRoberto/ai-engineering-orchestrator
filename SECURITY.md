# Security Policy

Do not report vulnerabilities in public issues. Use GitHub private vulnerability reporting when
enabled. Never commit credentials; local secrets belong in `.env`, which is ignored.

The service is read-only by default. Write requests stop at `WAITING_APPROVAL`. Protected branches,
force pushes and automated merges are blocked by `GitGovernanceService`. This foundation does not
execute arbitrary host commands or accept repository credentials.

