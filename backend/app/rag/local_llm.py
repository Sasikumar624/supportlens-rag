from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.config import get_settings


DEFAULT_LOCAL_LLM_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"


class LocalLLMModelType(StrEnum):
    CAUSAL = "causal"
    SEQ2SEQ = "seq2seq"


@dataclass(frozen=True)
class LocalLLMConfig:
    model_name: str = DEFAULT_LOCAL_LLM_MODEL
    model_type: LocalLLMModelType = LocalLLMModelType.CAUSAL
    max_new_tokens: int = 256
    temperature: float = 0.0
    do_sample: bool = False
    max_input_tokens: int = 2048

    def __post_init__(self) -> None:
        if not self.model_name.strip():
            raise ValueError("model_name cannot be empty")
        if self.max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")
        if self.temperature < 0:
            raise ValueError("temperature cannot be negative")
        if self.max_input_tokens <= 0:
            raise ValueError("max_input_tokens must be positive")


class LocalHuggingFaceLLMClient:
    def __init__(
        self,
        config: LocalLLMConfig | None = None,
        *,
        tokenizer: Any | None = None,
        model: Any | None = None,
    ) -> None:
        self.config = config or LocalLLMConfig()
        if tokenizer is None or model is None:
            tokenizer, model = _load_local_model(
                self.config.model_name,
                self.config.model_type,
            )
        self._tokenizer = tokenizer
        self._model = model

    @classmethod
    def from_settings(cls) -> "LocalHuggingFaceLLMClient":
        settings = get_settings()
        return cls(
            LocalLLMConfig(
                model_name=settings.llm_model or DEFAULT_LOCAL_LLM_MODEL,
                model_type=LocalLLMModelType(settings.llm_model_type),
                max_new_tokens=settings.llm_max_new_tokens,
                temperature=settings.llm_temperature,
                do_sample=settings.llm_do_sample,
            )
        )

    def generate(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("prompt cannot be empty")

        model_input = self._format_prompt(prompt)
        encoded = self._encode(model_input)
        output_ids = self._model.generate(
            **encoded,
            max_new_tokens=self.config.max_new_tokens,
            temperature=self.config.temperature,
            do_sample=self.config.do_sample,
        )
        decoded = self._tokenizer.decode(
            output_ids[0],
            skip_special_tokens=True,
        )
        return self._clean_decoded_output(decoded, model_input)

    def _format_prompt(self, prompt: str) -> str:
        if self.config.model_type != LocalLLMModelType.CAUSAL:
            return prompt

        apply_chat_template = getattr(self._tokenizer, "apply_chat_template", None)
        if apply_chat_template is None:
            return prompt

        return apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )

    def _encode(self, model_input: str) -> dict:
        encoded = self._tokenizer(
            model_input,
            return_tensors="pt",
            truncation=True,
            max_length=self.config.max_input_tokens,
        )
        model_device = getattr(self._model, "device", None)
        if model_device is None:
            return encoded
        return {
            key: value.to(model_device) if hasattr(value, "to") else value
            for key, value in encoded.items()
        }

    def _clean_decoded_output(self, decoded: str, model_input: str) -> str:
        text = decoded.strip()
        if self.config.model_type == LocalLLMModelType.CAUSAL and text.startswith(model_input):
            text = text[len(model_input) :].strip()
        return text


def _load_local_model(model_name: str, model_type: LocalLLMModelType):
    try:
        from transformers import AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as error:
        raise RuntimeError(
            "transformers is required for local LLM generation. "
            "Install backend/requirements.txt before loading the local model."
        ) from error

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if model_type == LocalLLMModelType.SEQ2SEQ:
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    else:
        model = AutoModelForCausalLM.from_pretrained(model_name)
    model.eval()
    return tokenizer, model
