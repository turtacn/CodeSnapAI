# Audit Logging

CodeSage provides an audit logging feature to track key governance actions.

## Configuration

Audit logging is configured in the `.codesage.yaml` file under the `audit` key.

- `enabled`: Enable or disable audit logging. Defaults to `true`.
- `log_dir`: The directory to store audit log files. Defaults to `.codesage/audit`.
- `max_file_size_mb`: The maximum size of a single audit log file in MB before rotation. Defaults to `10`.

## Log Format

Audit logs are written in the JSON Lines format, where each line is a JSON object representing an audit event.

### Audit Event Schema

- `timestamp`: The timestamp of the event.
- `event_type`: The type of event, e.g., `cli.snapshot.create`.
- `project_name`: The name of the project, if applicable.
- `command`: The command that was executed.
- `args`: The arguments passed to the command.
- `extra`: Additional context for the event.

## Privacy and Security

Audit logs do not contain any sensitive information such as account credentials. However, they do contain information about the projects being analyzed and the commands being run. Ensure that access to the audit log files is restricted to authorized personnel.
