# External Integration Hooks

CodeSage can be integrated with external systems using webhooks and file exports. These hooks provide a way to push read-only information about policy decisions, audit events, and regression warnings to other platforms.

## Webhooks

Webhooks can be used to send HTTP POST requests to a specified URL when certain events occur.

### Configuration

Webhooks are configured in the `.codesage.yaml` file under the `integrations.webhook` key.

- `url`: The URL to send the POST request to.
- `timeout_seconds`: The timeout for the request in seconds. Defaults to `10`.
- `headers`: A dictionary of headers to include in the request.
- `enabled`: Enable or disable the webhook. Defaults to `false`.

### Payload

The webhook payload is a JSON object with the following structure:

```json
{
  "event_type": "event_type",
  "payload": {
    // Event-specific data
  }
}
```

## File Export

Policy decisions and regression warnings can be exported to a specified directory as JSON files.

### Configuration

File export is configured in the `.codesage.yaml` file under the `integrations.file_export_dir` key.

- `file_export_dir`: The directory to export the files to.

### Exported Files

The exported files are named `policy_decisions_<timestamp>.json` and `regression_warnings_<timestamp>.json`. The content of these files is a JSON array of the corresponding objects.
