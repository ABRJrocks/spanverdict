# Data handling notice

SpanVerdict runs in the environment where you invoke it. The maintainer does not receive your files, agent inputs, outputs or credentials through the tool. There is no hosted service, analytics, account registration or telemetry upload in the core package or composite Action.

The checker reads the policy, candidate trace export and optional baseline you supply. It retains selected span identities, relationships, timing, operation/tool labels, case IDs and token counts to calculate the verdict. Raw export bytes are read into local process memory; prompts and other content may exist there until the process exits. Arbitrary attributes, span names, events and links are excluded from the normalized measurement model and generated reports.

Reports and baselines are written only to paths you specify and remain in your environment. Their retention and access depend on your filesystem and CI artifact settings. Reports retain measured usage and identifiers, which can themselves be sensitive. Delete local files and CI artifacts through your own storage controls when they are no longer needed.

The Action does not upload artifacts. A separate workflow step can publish them, and GitHub's own service rules govern that storage. Package installation and optional SDK dependency installation may contact the configured package index. The synthetic examples perform no model, customer-system or payment calls.

Support information you voluntarily submit to GitHub is handled through GitHub. Use synthetic reproductions and keep private files out of public issues. See [SECURITY.md](SECURITY.md) for private vulnerability reporting and operational limits.
