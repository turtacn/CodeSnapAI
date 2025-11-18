from codesage.llm.client import DummyLLMClient, LLMRequest


def test_dummy_client_returns_fixed_response():
    client = DummyLLMClient()
    request = LLMRequest(prompt="test prompt", model="dummy-model")
    response = client.generate(request)
    assert response.fix_hint
    assert response.rationale
