"""Xuất VietOCR vgg_seq2seq sang ONNX (CNN + encoder + decoder-step) để chạy bằng onnxruntime.

Cần gói `onnx` (pip install onnx) khi xuất; runtime chỉ cần onnxruntime.
"""
from __future__ import annotations

import os
import sys

import torch
import torch.nn as nn
import yaml


def _root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_pytorch():
    backend = _root()
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from vietocr.tool.config import Cfg
    from vietocr.tool.translate import build_model

    models = os.path.join(backend, "models", "vietocr")
    with open(os.path.join(models, "base.yml"), encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    with open(os.path.join(models, "vgg-seq2seq.yml"), encoding="utf-8") as handle:
        cfg.update(yaml.safe_load(handle) or {})
    cnn = dict(cfg.get("cnn") or {})
    cnn["pretrained"] = False
    cfg["cnn"] = cnn
    cfg["weights"] = os.path.join(models, "vgg_seq2seq.pth")
    cfg["device"] = "cpu"
    cfg["predictor"] = dict(cfg.get("predictor") or {}, beamsearch=False)
    model, vocab = build_model(Cfg(cfg))
    weights = torch.load(cfg["weights"], map_location="cpu")
    model.load_state_dict(weights)
    model.eval()
    return model, vocab, models


class _Cnn(nn.Module):
    """VGG permute(-1) phá type-inference ONNX khi width động — dùng permute tường minh."""

    def __init__(self, cnn):
        super().__init__()
        vgg = cnn.model
        self.features = vgg.features
        self.dropout = vgg.dropout
        self.last_conv_1x1 = vgg.last_conv_1x1

    def forward(self, image):
        conv = self.last_conv_1x1(self.dropout(self.features(image)))
        conv = conv.permute(0, 1, 3, 2).contiguous()
        conv = torch.flatten(conv, start_dim=2)
        return conv.permute(2, 0, 1).contiguous()


class _Encoder(nn.Module):
    def __init__(self, encoder):
        super().__init__()
        self.encoder = encoder

    def forward(self, src):
        outputs, hidden = self.encoder(src)
        return outputs, hidden


class _DecoderStep(nn.Module):
    """Một bước decoder, không dùng assert của VietOCR (phá tracing ONNX)."""

    def __init__(self, decoder):
        super().__init__()
        self.embedding = decoder.embedding
        self.attention = decoder.attention
        self.rnn = decoder.rnn
        self.fc_out = decoder.fc_out
        self.dropout = decoder.dropout

    def forward(self, token, hidden, encoder_outputs):
        embedded = self.dropout(self.embedding(token.unsqueeze(0)))
        attn = self.attention(hidden, encoder_outputs).unsqueeze(1)
        weighted = torch.bmm(attn, encoder_outputs.permute(1, 0, 2)).permute(1, 0, 2)
        output, hidden = self.rnn(torch.cat((embedded, weighted), dim=2), hidden.unsqueeze(0))
        logits = self.fc_out(
            torch.cat((output.squeeze(0), weighted.squeeze(0), embedded.squeeze(0)), dim=1)
        )
        return logits, hidden.squeeze(0)


def export() -> None:
    model, vocab, models = load_pytorch()
    os.makedirs(models, exist_ok=True)
    with open(os.path.join(models, "vocab.txt"), "w", encoding="utf-8") as handle:
        handle.write(vocab.chars)

    dummy_w = 160
    image = torch.randn(1, 3, 32, dummy_w)
    with torch.no_grad():
        src = model.cnn(image)
    src_len = src.shape[0]
    hidden, enc_out = model.transformer.forward_encoder(src)
    token = torch.zeros(1, dtype=torch.long)

    cnn = _Cnn(model.cnn).eval()
    enc = _Encoder(model.transformer.encoder).eval()
    dec = _DecoderStep(model.transformer.decoder).eval()

    _kw = dict(opset_version=17, dynamo=False, do_constant_folding=True)
    torch.onnx.export(
        cnn,
        image,
        os.path.join(models, "cnn.onnx"),
        input_names=["image"],
        output_names=["src"],
        dynamic_axes={"image": {3: "width"}, "src": {0: "src_len"}},
        **_kw,
    )
    torch.onnx.export(
        enc,
        src,
        os.path.join(models, "encoder.onnx"),
        input_names=["src"],
        output_names=["encoder_outputs", "hidden"],
        dynamic_axes={
            "src": {0: "src_len"},
            "encoder_outputs": {0: "src_len"},
        },
        **_kw,
    )
    torch.onnx.export(
        dec,
        (token, hidden, enc_out),
        os.path.join(models, "decoder.onnx"),
        input_names=["token", "hidden", "encoder_outputs"],
        output_names=["logits", "hidden_out"],
        dynamic_axes={"encoder_outputs": {0: "src_len"}},
        **_kw,
    )
    import onnxruntime as ort

    sess = ort.InferenceSession(os.path.join(models, "cnn.onnx"), providers=["CPUExecutionProvider"])
    src_np = sess.run(None, {"image": image.numpy()})[0]
    print("exported", models, "src_len", src_len, "cnn_out", src_np.shape, "vocab", len(vocab))


if __name__ == "__main__":
    export()
