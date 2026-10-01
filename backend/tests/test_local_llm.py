from app.rag.local_llm import (
    DEFAULT_LOCAL_LLM_MODEL,
    LazyLocalHuggingFaceLLMClient,
    LocalHuggingFaceLLMClient,
    LocalLLMConfig,
    LocalLLMModelType,
)


class FakeTokenizer:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.decoded: list = []

    def __call__(
        self,
        prompt: str,
        *,
        return_tensors: str,
        truncation: bool,
        max_length: int,
    ) -> dict:
        self.calls.append(
            {
                "prompt": prompt,
                "return_tensors": return_tensors,
                "truncation": truncation,
                "max_length": max_length,
            }
        )
        return {"input_ids": [[1, 2, 3]], "attention_mask": [[1, 1, 1]]}

    def decode(self, output_ids, *, skip_special_tokens: bool) -> str:
        self.decoded.append(output_ids)
        assert skip_special_tokens is True
        return " Use the reset button. [1] "


class FakeChatTokenizer(FakeTokenizer):
    def apply_chat_template(
        self,
        messages,
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        assert tokenize is False
        assert add_generation_prompt is True
        return f"<user>{messages[0]['content']}</user><assistant>"

    def decode(self, output_ids, *, skip_special_tokens: bool) -> str:
        self.decoded.append(output_ids)
        assert skip_special_tokens is True
        return "<user>Grounded prompt</user><assistant>Use the reset button. [1]"


class FakeModel:
    def __init__(self) -> None:
        self.generate_calls: list[dict] = []

    def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        return [[9, 8, 7]]


def test_local_huggingface_client_tokenizes_generates_and_decodes() -> None:
    tokenizer = FakeTokenizer()
    model = FakeModel()
    client = LocalHuggingFaceLLMClient(
        LocalLLMConfig(
            model_name="fake-model",
            max_new_tokens=64,
            temperature=0.2,
            do_sample=True,
            max_input_tokens=512,
        ),
        tokenizer=tokenizer,
        model=model,
    )

    answer = client.generate("Grounded prompt")

    assert answer == "Use the reset button. [1]"
    assert tokenizer.calls == [
        {
            "prompt": "Grounded prompt",
            "return_tensors": "pt",
            "truncation": True,
            "max_length": 512,
        }
    ]
    assert model.generate_calls[0]["max_new_tokens"] == 64
    assert model.generate_calls[0]["temperature"] == 0.2
    assert model.generate_calls[0]["do_sample"] is True


def test_local_huggingface_client_uses_chat_template_for_causal_models() -> None:
    tokenizer = FakeChatTokenizer()
    model = FakeModel()
    client = LocalHuggingFaceLLMClient(
        LocalLLMConfig(model_name="fake-model", model_type=LocalLLMModelType.CAUSAL),
        tokenizer=tokenizer,
        model=model,
    )

    answer = client.generate("Grounded prompt")

    assert answer == "Use the reset button. [1]"
    assert tokenizer.calls[0]["prompt"] == "<user>Grounded prompt</user><assistant>"


def test_default_local_model_is_stronger_instruct_candidate() -> None:
    assert DEFAULT_LOCAL_LLM_MODEL == "Qwen/Qwen2.5-1.5B-Instruct"
    assert LocalLLMConfig().model_type == LocalLLMModelType.CAUSAL


def test_local_huggingface_client_rejects_empty_prompts() -> None:
    client = LocalHuggingFaceLLMClient(
        LocalLLMConfig(model_name="fake-model"),
        tokenizer=FakeTokenizer(),
        model=FakeModel(),
    )

    try:
        client.generate(" ")
    except ValueError as error:
        assert "prompt" in str(error)
    else:
        raise AssertionError("Expected prompt validation error")


def test_lazy_local_huggingface_client_rejects_uncached_model(monkeypatch) -> None:
    monkeypatch.setenv("HF_HOME", "Z:/supportlens-missing-hf-cache")
    client = LazyLocalHuggingFaceLLMClient(
        LocalLLMConfig(model_name="missing/model")
    )

    try:
        client.generate("Grounded prompt")
    except RuntimeError as error:
        assert "not cached" in str(error)
    else:
        raise AssertionError("Expected uncached model error")


def test_local_llm_config_validates_generation_settings() -> None:
    try:
        LocalLLMConfig(model_name=" ")
    except ValueError as error:
        assert "model_name" in str(error)
    else:
        raise AssertionError("Expected model_name validation error")

    try:
        LocalLLMConfig(max_new_tokens=0)
    except ValueError as error:
        assert "max_new_tokens" in str(error)
    else:
        raise AssertionError("Expected max_new_tokens validation error")

    try:
        LocalLLMConfig(temperature=-0.1)
    except ValueError as error:
        assert "temperature" in str(error)
    else:
        raise AssertionError("Expected temperature validation error")
