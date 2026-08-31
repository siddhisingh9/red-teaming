import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"

_tok = None
_model = None


def _load():
    """Load once, on first call. Keeps import cheap and CPU-only-safe."""
    global _tok, _model
    if _model is not None:
        return
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    _tok = AutoTokenizer.from_pretrained(MODEL_ID)
    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, quantization_config=bnb, device_map="auto"
    )
    _model.eval()


@torch.inference_mode()
def _run(messages, max_new_tokens, temperature):
    _load()
    text = _tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    ids = _tok(text, return_tensors="pt").to(_model.device)
    out = _model.generate(
        **ids,
        max_new_tokens=max_new_tokens,
        do_sample=temperature > 0,
        temperature=temperature if temperature > 0 else None,
        top_p=None,
        top_k=None,
        pad_token_id=_tok.eos_token_id,
    )
    new_ids = out[0][ids["input_ids"].shape[1]:]
    return _tok.decode(new_ids, skip_special_tokens=True), len(new_ids)


def generate(messages, max_new_tokens=512, temperature=0.0) -> str:
    return _run(messages, max_new_tokens, temperature)[0]


def generate_with_stats(messages, max_new_tokens=512, temperature=0.0):
    """(text, n_new_tokens) — for benchmarking."""
    return _run(messages, max_new_tokens, temperature)
