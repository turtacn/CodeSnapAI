from pytest_httpserver import HTTPServer
from codesage.integrations.webhook import WebhookConfig, WebhookClient

def test_webhook_client_sends_post_with_payload(httpserver: HTTPServer):
    config = WebhookConfig(
        url=httpserver.url_for("/"),
        enabled=True
    )
    httpserver.expect_request("/", method="POST").respond_with_json({"status": "ok"})

    client = WebhookClient(config)
    event_type = "policy_decision"
    payload = {"rule_id": "test-rule", "severity": "error"}
    client.send(event_type, payload)

    httpserver.check_assertions()
    request, _ = httpserver.log[0]
    assert request.get_json() == {
        "event_type": "policy_decision",
        "payload": {"rule_id": "test-rule", "severity": "error"}
    }
