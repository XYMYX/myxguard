# Security policy

MyxGuard is a heuristic scanner. It is not a security boundary. A clean scan does not mean the text is safe to give to an agent, and a high score does not mean the text is an attack. Keep a human or a stricter control in the path if the decision matters.

The program does not send text anywhere. There is no telemetry. `scan` and the MCP server only read what you pass them and write a report to the caller.

## Reporting a problem

Please do not open a public issue that contains a working bypass, a weaponised prompt, or step-by-step exploit detail.

If this repository is hosted on GitHub, use a private security advisory for the repository (GitHub: Security → Advisories → Report a vulnerability). Otherwise contact the maintainer, XYMYX, through a private channel. There is no public email address in this tree.

Include the MyxGuard version (`python -m myxguard --version`), the smallest input that shows the problem, and whether you expected a finding or expected silence.

We will confirm receipt when we see the report and will keep the detail private until a fix is in the tree, unless you agree to something else.
