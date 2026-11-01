"""OCR mặt trước CCCD gắn chip: deskew → cắt ROI → VietOCR ONNX → regex.

Pipeline:
1. Tìm 4 góc thẻ (findContours) rồi warpPerspective về khổ ISO ID-1 cố định.
2. Cắt 5 vùng chữ theo toạ độ tương đối (số CCCD, họ tên, ngày sinh, giới tính, hàng dưới).
3. Nhận từng ROI bằng VietOCR vgg_seq2seq (onnxruntime, CPU).
4. Chuẩn hoá: 12 số / DD/MM/YYYY / Nam|Nữ; họ tên bỏ dấu tiếng Việt.

parse_cccd_lines() vẫn dùng cho API test (monkeypatch read_lines).
"""
from __future__ import annotations

import os
import re
import threading
import time
import unicodedata
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

CARD_RATIO = 85.6 / 53.98          # Tỉ lệ chuẩn ISO/IEC 7810 ID-1
WARP_W = 1200
WARP_H = int(round(WARP_W / CARD_RATIO))
OCR_MAX_W = 640
_VIETOCR_DIR = os.path.join(os.path.dirname(__file__), "models", "vietocr")

MIN_SHARPNESS = 22.0               # Phương sai Laplacian tối thiểu ở Pha 1 (nới nhạy cho webcam)
MIN_SHARPNESS_ZOOM = 10.0          # Ngưỡng nét nới lỏng tối đa ở Pha 2 khi zoom gần
MIN_BRIGHTNESS = 40.0
MAX_BRIGHTNESS = 250.0
MAX_GLARE_RATIO = 0.18             # Tỉ lệ pixel cháy sáng tối đa

FIELDS = ("id_number", "full_name", "dob", "gender")

# Toạ độ tương đối trên CCCD gắn chip (ảnh chân dung trái ~30%, chữ bên phải).
# (x0, y0, x1, y1) theo ảnh đã warp khổ WARP_W x WARP_H.
CHIP_ROIS = {
    "id_number": (0.30, 0.22, 0.995, 0.38),
    "full_name": (0.28, 0.36, 0.995, 0.56),  # nhãn + cả dòng họ-đệm-tên
    "dob": (0.30, 0.52, 0.72, 0.68),
    # Chỉ ô giá trị Nam/Nữ — cắt trước Quốc tịch / Việt Nam, không lấy quê quán.
    "sex": (0.32, 0.56, 0.56, 0.71),
    "lower_row": (0.30, 0.52, 0.995, 0.80),
}
# Căn cước 2024: thêm dòng Identity / Số định danh; DOB+Sex nhãn một hàng, giá trị hàng dưới.
CHIP_ROIS_NEW = {
    "id_number": (0.30, 0.26, 0.995, 0.46),
    "full_name": (0.26, 0.40, 0.995, 0.62),
    "dob": (0.28, 0.54, 0.64, 0.80),
    "sex": (0.50, 0.54, 0.94, 0.80),
    "lower_row": (0.26, 0.50, 0.995, 0.86),
}
ROI_MAX_LEN = {
    "id_number": 20,
    "full_name": 48,
    "dob": 18,
    "sex": 16,
    "lower_row": 36,
}
ROI_MAX_WIDTH = {
    "id_number": 480,
    "full_name": 800,
    "dob": 320,
    "sex": 240,
    "lower_row": 512,
}


# -----------------------------------------------------------------------------
# Tiện ích chuỗi tiếng Việt & sửa lỗi ký tự số của OCR
# -----------------------------------------------------------------------------

def fold(text: str) -> str:
    """Bỏ dấu tiếng Việt + chữ thường để so khớp nhãn bền vững với lỗi OCR."""
    return plain_name(text).lower()


def plain_name(text: str) -> str:
    """Bỏ dấu tiếng Việt, giữ nguyên hoa/thường."""
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")


_DIGIT_FIX = str.maketrans({
    "O": "0", "o": "0", "D": "0", "Q": "0", "U": "0",
    "I": "1", "l": "1", "|": "1", "i": "1", "!": "1",
    "Z": "2", "z": "2",
    "S": "5", "s": "5",
    "G": "6", "b": "6",
    "B": "8",
})


def _fix_digit_tokens(line: str) -> str:
    """Sửa lỗi OCR nhầm chữ/số (O->0, I->1, S->5...) trong các cụm có chứa chữ số."""
    out = []
    for tok in line.split(" "):
        core = re.sub(r"[^0-9A-Za-z|!]", "", tok)
        digits = sum(c.isdigit() for c in core)
        if (len(core) >= 2 and digits / len(core) >= 0.4) or digits >= 2:
            tok = tok.translate(_DIGIT_FIX)
        out.append(tok)
    return " ".join(out)


# Nhãn & cụm tiêu đề cố định trên thẻ (dạng đã bỏ dấu) - tuyệt đối loại khỏi ứng viên họ tên
_LABEL_WORDS = (
    "cong hoa", "xa hoi", "chu nghia", "viet nam", "doc lap", "tu do", "hanh phuc", "can cuoc",
    "cong dan", "citizen", "identity", "card", "socialist", "republic", "independence", "freedom",
    "happiness", "ho va ten", "full name", "ngay sinh", "date of birth", "gioi tinh", "sex",
    "quoc tich", "nationality", "que quan", "place of", "noi thuong tru", "residence", "co gia tri",
    "date of expiry", "so dinh danh", "personal", "identification", "number", "chu dem", "surname",
    "given name", "middle name", "khai sinh", "noi cu tru", "noi dang ky",
)

# Regex bắt mọi biến thể OCR đọc nhầm tiêu đề "CĂN CƯỚC CÔNG DÂN" / "CỘNG HÒA..." / nhãn tiếng Anh
_NON_NAME_FUZZY_RE = re.compile(
    r"("
    r"c[aăâe]n\s*c[uưo0ơu][o0ơu]?[ce]|\bc[uưo0ơ]{1,2}c\s*c[o0ô]ng\b|c[o0ô]ng\s*[dđo0]a?n|"
    r"c[o0ộ]ng\s*h[o0ò]a|x[aã]\s*h[o0ộ]i|ch[uủ]\s*ngh[iĩ]a|[dđ][o0ộ]c\s*l[aăậ]p|h[aạ]nh\s*ph[uú]c|"
    r"ng[aà]y\s*sinh|gi[o0ớ]i\s*t[ií]nh|qu[o0ố]c\s*t[iị]ch|qu[eê]\s*qu[aá]n|th[uư][oơờ]ng\s*tr[uú]|"
    r"gi[aá]\s*tr[iị]|k[h]ai\s*sinh|ch[uữ]\s*[dđ][eệ]m|[dđ][iị]nh\s*danh|"
    r"\b(?:citizen|identity|card|socialist|republic|independence|freedom|happiness|"
    r"full|name|surname|given|middle|date|birth|sex|nationality|place|origin|residence|expiry|"
    r"personal|identification|number)\b"
    r")",
    re.IGNORECASE,
)

_NAME_LABEL_RE = re.compile(
    r"(ho\s*,?\s*chu\s*dem|ho\s*va\s*ten|full\s*name|chu\s*dem|"
    r"surname|given\s*name|middle\s*name|ten\s*khai\s*sinh)"
)
_INLINE_NAME_PREFIX_RE = re.compile(
    r"^.*(?:full\s*name|given\s*name|middle\s*name|surname|khai\s*sinh|"
    r"ho\s*,?\s*chu\s*dem|ho\s*va\s*ten)\s*[:/.\-]*\s*",
    re.IGNORECASE,
)
_DOB_LABEL_RE = re.compile(
    r"(ng[aà]y\s*,?\s*th[aá]ng|ng[aàv]y\s*s[i1l]nh|n[aă]m\s*s[i1l]nh|date\s*[o0]f\s*b[i1l]rth|\bb[i1l]rth\b|\bd[o0]b\b)"
)
_EXPIRY_LINE_RE = re.compile(r"(c[o0]\s*g[i1l]a\s*tr[i1l]|g[i1l]a\s*tr[i1l]\s*d[eê]n|date\s*[o0]f\s*exp|exp[i1l]ry)")
_SEX_LABEL_RE = re.compile(r"(g[i1l][o0d]i\s*t[i1l]nh|gi[o0]i\s*tinh|\bs[e3]x\b|\bgi[o0]i\b)")
_VIET_NAM_RE = re.compile(
    r"v[i1ly][eêaăo0]{0,2}t\s*n[aă]r?[mn]|\bvietnam\b"
)
_PLACE_NAM_RE = re.compile(
    r"\b(?:nam\s*dinh|ha\s*nam|quang\s*nam|nam\s*dan|nam\s*truc|nam\s*d[i1]nh)\b"
)
_NU_TOKEN_RE = re.compile(
    r"(?:^|[\s:.;,/\-]|sex|tinh)"
    r"(nu|nv|nw|nii|nir|nuh|nue|nux|nư|female|femele|fem)"
    r"(?=$|[\s,.;:/\-]|qu|na|tich|national)"
)
_NAM_TOKEN_RE = re.compile(
    r"(?:^|[\s:.;,/\-]|sex|tinh)"
    r"(nam|narn|nanm|male)"
    r"(?=$|[\s,.;:/\-]|qu|tich|national)"
)
_STOP_RE = re.compile(
    r"(qu[o0ôơ]c\s*t[i1l]ch|nat[i1l][o0]n|qu[eê]\s*qu[aá]n|place\s*[o0]f|n[o0ơ]i\s*th|n[o0ơ]i\s*cu|n[o0ơ]i\s*dang|res[i1l]d|c[o0]\s*g[i1l]a\s*tr)"
)
_ADDRESS_START_RE = re.compile(
    r"(qu[eê]\s*qu[aá]n|place\s*[o0]f\s*[o0]r[i1l]g|n[o0ơ]i\s*th[uư][o0ơ]ng|place\s*[o0]f\s*res|n[o0ơ]i\s*cu\s*tru|n[o0ơ]i\s*dang\s*ky)"
)
# Đơn vị hành chính / cụm địa danh trên CCCD — không phải họ tên
_ADMIN_UNIT_RE = re.compile(
    r"\b(thi\s*tran|thi\s*xa|thanh\s*pho|\btp\b|tphcm|"
    r"quan\s*(?:1[0-2]|[1-9])|khu\s*pho|to\s*dan\s*pho|so\s*nha)\b"
)
_PLACE_PHRASES = frozenset((
    "nha be", "can gio", "cu chi", "hoc mon", "binh chanh", "thu duc",
    "go vap", "binh thanh", "tan binh", "tan phu", "phu nhuan", "binh tan",
    "ho chi minh", "hai phong", "da nang", "can tho",
    "vung tau", "ba ria", "nha trang", "da lat", "bien hoa",
    "phu xuan nha be",
))

# Bắt ngày sinh: cho phép cả trường hợp dấu ':' trước ngày bị đọc nhầm thành số '1',
# dấu '/' bị đọc nhầm thành '1'/'7'/'|' hoặc khoảng trắng, hoặc bị nuốt mất ('15082003')
_DATE_SEP_RE = re.compile(r"(\d{1,2})\s*[/\-.,:]\s*(\d{1,2})\s*[/\-.,:\s]\s*((?:19|20)\d{2})(?!\d)")
_DATE_SPACE_RE = re.compile(r"(?<!\d)(\d{1,2})\s+(\d{1,2})\s+((?:19|20)\d{2})(?!\d)")
_DATE_FLEX_RE = re.compile(
    r"(\d{2})(?:[/\-.,:\s]|[17|lI])?(\d{2})(?:[/\-.,:\s]|[17|lI])?((?:19|20)\d{2})(?!\d)"
)
_ID_RE = re.compile(r"(?<!\d)(\d{12})(?!\d)")
_ID_CHUNK_RE = re.compile(r"\d(?:[\s.\-/:|,]*\d){11}")
# 3 số đầu: mã tỉnh/thành lúc cấp CCCD (63 tỉnh cũ). Không loại cứng mã lạ.
_CCCD_PROVINCE = frozenset((
    "001", "002", "004", "006", "008", "010", "011", "012", "014", "015",
    "017", "019", "020", "022", "024", "025", "026", "027", "030", "031",
    "033", "034", "035", "036", "037", "038", "040", "042", "044", "045",
    "046", "048", "049", "051", "052", "054", "056", "058", "060", "062",
    "064", "066", "067", "068", "070", "072", "074", "075", "077", "079",
    "080", "082", "083", "084", "086", "087", "089", "091", "092", "093",
    "094", "095", "096",
))
_CARD_KEYWORDS = (
    "can cuoc", "cong dan", "citizen", "identity", "identity card", "cong hoa",
    "socialist", "ho va ten", "full name", "date of birth", "ngay sinh",
    "gioi tinh", "quoc tich", "nationality", "viet nam", "dinh danh",
    "personal identification", "so / no", "so/no",
)


def _is_address_text(text: str) -> bool:
    """Quê quán / nơi thường trú — không được đưa vào họ tên."""
    if not text:
        return False
    folded = fold(text)
    if _ADDRESS_START_RE.search(folded) or _ADMIN_UNIT_RE.search(folded):
        return True
    if _STOP_RE.search(folded) and not _NAME_LABEL_RE.search(folded):
        return True
    compact = re.sub(r"\s+", " ", folded)
    padded = f" {compact} "
    for phrase in _PLACE_PHRASES:
        if f" {phrase} " in padded:
            return True
    # "Họ, chữ đệm và tên khai sinh" trên Căn cước 2024 có dấu phẩy — không phải địa chỉ.
    if (
        "," in text
        and len([p for p in text.split(",") if p.strip()]) >= 2
        and not _NAME_LABEL_RE.search(folded)
    ):
        return True
    return False


def _looks_like_name(text: str) -> bool:
    cleaned = _clean_name(text)
    letters = [c for c in cleaned if c.isalpha()]
    if len(letters) < 4 or any(c.isdigit() for c in text):
        return False
    words = [w for w in cleaned.split() if w]
    if not (2 <= len(words) <= 5):
        return False
    orig_letters = [c for c in text if c.isalpha()]
    upper_ratio = sum(c.isupper() for c in orig_letters) / max(1, len(orig_letters))
    if upper_ratio < 0.65:
        return False
    f = fold(cleaned)
    if any(lbl in f for lbl in _LABEL_WORDS):
        return False
    if _NON_NAME_FUZZY_RE.search(f):
        return False
    if _is_address_text(text) or _is_address_text(cleaned):
        return False
    if fold(words[0]) not in _COMMON_SURNAMES:
        return False
    return True


def _clean_name(text: str) -> str:
    text = fold(text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.upper()


_NAME_KEEP_RE = re.compile(r"[^A-Za-zÀ-ỹĐđĂăÂâÊêÔôƠơƯư\s\-']")
_NAME_LABEL_STRIP_RE = re.compile(
    r"(?i)(họ[^:]{0,40}tên|full\s*name|ho\s*va\s*ten|chu\s*dem|surname|given\s*name)[:.\-/]*"
)
_NAME_STOP = {
    "full", "name", "date", "birth", "sex", "card", "citizen", "identity",
    "surname", "given", "middle", "nationality", "residence", "expiry",
    "personal", "number", "of", "and", "the", "va", "ten", "chu", "dem",
    "khai", "sinh", "gioi", "tinh", "ngay", "thang",
}
# Từ OCR hay dính từ dòng Sex / Ngày sinh — cắt tên ngay trước chúng.
# Không đưa "quoc" vào đây: "Quốc" là tên người; chỉ cắt cụm "Quốc tịch".
_NAME_JUNK = {
    "sex", "sch", "sai", "nghie", "nhinh", "sinh", "ngay", "birth", "date",
    "gioi", "tinh", "tich", "card", "full", "name", "male", "female",
    "identity", "citizen", "number", "personal", "dob", "no",
}
_NAME_JUNK_BEFORE_GENDER = {"sai", "sex", "sch", "gioi", "tinh"}
_COMMON_SURNAMES = {
    "nguyen", "tran", "le", "pham", "hoang", "huynh", "phan", "vu", "vo",
    "dang", "bui", "do", "duong", "ngo", "ly", "truong", "doan", "trinh",
    "mai", "cao", "luu", "thai", "ton", "to", "ho", "ha", "dao", "dinh",
    "lam", "luong", "chau", "kieu", "tang", "nghiem", "thach", "mac",
    "la", "tieu", "ung", "giap", "quyen", "ong", "au", "ta", "tu",
    "tong", "kim", "chu", "han", "lu", "che", "quach", "phung", "giang",
    "vuong", "trang", "hong", "bach", "diep", "khuat", "lao", "nghiep",
}
# "Thị" / "Văn" là chữ đệm — "NGUYEN THI" chưa phải họ tên đầy đủ
_NAME_PARTICLES = {"thi", "van", "huu", "duc", "cong", "dinh"}
_VN_VOWELS = set("aeiouyăâêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵđ")


def _is_name_junk(word: str, prev: Optional[str] = None) -> bool:
    token = fold(word)
    if token in _NAME_JUNK:
        return True
    if token in {"nam", "nu", "nữ"} and fold(prev or "") in _NAME_JUNK_BEFORE_GENDER:
        return True
    if re.search(r"\d", word):
        return True
    return False


def _vn_name_syllable(word: str) -> bool:
    token = fold(word)
    if len(token) == 1:
        return token in {"y", "i"}
    if not (2 <= len(token) <= 8):
        return False
    if not re.fullmatch(r"[a-zđ]+", token):
        return False
    if not any(ch in "aeiouy" for ch in token):
        return False
    if token in _NAME_JUNK:
        return False
    return True


def _name_words(text: str) -> List[str]:
    """Chỉ giữ các tiếng trước khi đụng nhãn Sex/Ngày sinh/Quốc tịch."""
    raw = _NAME_LABEL_STRIP_RE.sub(" ", text or "")
    raw = _NAME_KEEP_RE.sub(" ", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" -")
    tokens = raw.split()
    words: List[str] = []
    prev = None
    for idx, word in enumerate(tokens):
        if not word or fold(word) in _NAME_STOP:
            continue
        nxt = fold(tokens[idx + 1]) if idx + 1 < len(tokens) else ""
        if fold(word) == "quoc" and nxt == "tich":
            break
        if _is_name_junk(word, prev):
            break
        if not _vn_name_syllable(word):
            break
        words.append(word)
        prev = word
        if len(words) >= 5:
            break
    if len(words) >= 4 and fold(words[0]) in {"ho", "h0"}:
        words = words[1:]
    return words


def _is_incomplete_name(name: Optional[str]) -> bool:
    """Họ + Thị/Văn chưa có tên gọi — chưa chốt. Hai tiếng khác vẫn hiện HUD, ưu tiên đủ 3."""
    if not name:
        return True
    parts = [w for w in name.split() if w]
    if len(parts) >= 3:
        return False
    if len(parts) < 2:
        return True
    return fold(parts[1]) in _NAME_PARTICLES


def _name_score(name: str) -> float:
    if not name:
        return -1.0
    parts = [w for w in name.split() if w]
    if not (2 <= len(parts) <= 5):
        return -1.0
    folded = fold(name)
    if _is_address_text(name) or _is_address_text(folded):
        return -1.0
    if any(lbl in folded for lbl in _LABEL_WORDS):
        return -1.0
    if _NON_NAME_FUZZY_RE.search(folded):
        return -1.0
    if any(_is_name_junk(w) for w in parts):
        return -1.0
    for word in parts:
        if not _vn_name_syllable(word):
            return -1.0
    if fold(parts[0]) not in _COMMON_SURNAMES:
        return -1.0
    if _is_incomplete_name(name):
        return 2.0
    score = float(len(parts) * 3)
    if 3 <= len(parts) <= 4:
        score += 8
    elif len(parts) == 2:
        score += 1
    elif len(parts) == 5:
        score += 4
    score += min(4.0, sum(1 for ch in name if ord(ch) > 127) * 0.6)
    score += 3
    if fold(parts[0]) == "ho" and len(parts) >= 4:
        score -= 5
    return score


def pretty_name(text: str) -> Optional[str]:
    """Họ tên: lấy các tiếng đầu (họ→đệm→tên), cắt trước Sex/Ngày sinh."""
    words = _name_words(text)
    if len(words) < 2:
        return None
    best: Optional[str] = None
    best_score = 5.5
    # Ưu tiên 3–4 tiếng từ ĐẦU chuỗi (họ đứng trước), không lấy đuôi dính nhãn
    for count in range(min(5, len(words)), 1, -1):
        cand = " ".join(words[:count]).upper()
        if any(ch.isdigit() for ch in cand):
            continue
        score = _name_score(cand)
        if score > best_score:
            best, best_score = cand, score
    return plain_name(best).upper() if best else None


def _folded_parts(words: List[str]) -> List[str]:
    return [fold(w) for w in words]


def _is_name_prefix(short: List[str], long: List[str]) -> bool:
    if not short or len(short) > len(long):
        return False
    return _folded_parts(long)[: len(short)] == _folded_parts(short)


def _extend_name(base: List[str], extra: List[str]) -> List[str]:
    """Ghép mảnh OCR: 'NGUYEN VAN' + 'AN' → đủ họ-đệm-tên. Không đổi sang người khác."""
    extra = [w for w in extra if _vn_name_syllable(w) and fold(w) not in _NAME_STOP]
    if not extra:
        return base
    if not base:
        return extra[:5]
    extra_f0 = fold(extra[0])
    if extra_f0 in _COMMON_SURNAMES:
        if _is_name_prefix(base, extra) and len(extra) > len(base):
            return extra[:5]
        if _is_name_prefix(extra, base):
            return base
        return base
    if _is_name_prefix(extra, base):
        return base
    base_f = _folded_parts(base)
    extra_f = _folded_parts(extra)
    for overlap in range(min(len(base_f), len(extra_f)), 0, -1):
        if base_f[-overlap:] == extra_f[:overlap]:
            return (base + extra[overlap:])[:5]
    if extra_f0 in _COMMON_SURNAMES:
        return base
    seen = set(base_f)
    out = list(base)
    for word, token in zip(extra, extra_f):
        if token in seen or token in _COMMON_SURNAMES:
            continue
        out.append(word)
        seen.add(token)
        if len(out) >= 4:
            break
    return out


def pick_name(*texts: str) -> Optional[str]:
    """Ghép đủ 3–4 tiếng họ-đệm-tên trong dải giữa ID và Ngày sinh; không lấy địa chỉ."""
    collected: List[str] = []
    best: Optional[str] = None
    best_score = 5.5
    stop_rest = False
    for text in texts:
        if stop_rest:
            break
        if not text:
            continue
        for chunk in re.split(r"[\n|]+", text):
            if not chunk:
                continue
            folded = fold(chunk)
            if _ADDRESS_START_RE.search(folded) or _STOP_RE.search(folded) or _SEX_LABEL_RE.search(folded):
                stop_rest = True
                break
            if pick_dob(chunk) and _DOB_LABEL_RE.search(folded):
                stop_rest = True
                break
            if _ADMIN_UNIT_RE.search(folded) or _is_address_text(chunk):
                continue
            words = _name_words(chunk)
            if not words:
                continue
            collected = _extend_name(collected, words)
            for source in (collected, words):
                cand = pretty_name(" ".join(source))
                if not cand:
                    continue
                if best:
                    best_p, cand_p = best.split(), cand.split()
                    if fold(best_p[0]) != fold(cand_p[0]) and not _is_incomplete_name(best):
                        continue
                    if (
                        len(best_p) >= 3
                        and not _is_name_prefix(best_p, cand_p)
                        and not _is_name_prefix(cand_p, best_p)
                    ):
                        continue
                score = _name_score(cand)
                if score > best_score:
                    best, best_score = cand, score
    if best:
        return best
    if (
        len(collected) >= 2
        and fold(collected[0]) in _COMMON_SURNAMES
        and not _is_address_text(" ".join(collected[:2]))
    ):
        return plain_name(" ".join(collected[: min(5, len(collected))])).upper()
    return None


def valid_person_name(name: Optional[str]) -> Optional[str]:
    """Họ tên đủ để chốt: không phải địa chỉ, không phải mới họ+Thị/Văn."""
    if not name:
        return None
    cand = pretty_name(name)
    if cand and not _is_incomplete_name(cand) and _name_score(cand) >= 8:
        return cand
    return None


def draft_person_name(name: Optional[str]) -> Optional[str]:
    """Tên hiện trên HUD khi đang đọc — kể cả mới 2 tiếng."""
    if not name or _is_address_text(name):
        return None
    good = valid_person_name(name)
    if good:
        return good
    cand = pretty_name(name)
    if cand:
        return cand
    words = _name_words(name)
    if len(words) >= 2 and fold(words[0]) in _COMMON_SURNAMES:
        draft = plain_name(" ".join(words[: min(5, len(words))])).upper()
        if not _is_address_text(draft):
            return draft
    return None


def prefer_name(old: Optional[str], new: Optional[str]) -> Optional[str]:
    """Giữ tên đã đúng; chỉ nối thêm tiếng khi cùng họ-đệm. Không nhảy sang tên khác."""
    new = valid_person_name(new)
    old = valid_person_name(old)
    if not new:
        return old or None
    if not old:
        return new
    old_p = old.split()
    new_p = new.split()
    if _is_name_prefix(old_p, new_p) and len(new_p) > len(old_p):
        return new
    if _is_name_prefix(new_p, old_p):
        return old
    if _folded_parts(old_p) == _folded_parts(new_p):
        return old if _name_score(old) >= _name_score(new) else new
    if fold(old_p[0]) != fold(new_p[0]):
        return old
    if len(old_p) >= 3:
        return old
    if len(new_p) >= 3:
        return new
    return old if _name_score(old) + 0.4 >= _name_score(new) else new


def _digit_runs_12(text: str) -> List[str]:
    """Cụm đúng 12 số, cho phép cách/chấm/gạch. Không ghép số từ cả dòng."""
    if not text:
        return []
    found: List[str] = []
    for match in _ID_CHUNK_RE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) == 12 and digits not in found:
            found.append(digits)
    return found


def normalize_id_number(text: str) -> Optional[str]:
    """12 chữ số. Ưu tiên cụm số sẵn có; chỉ sửa O/D/I/l/B khi thiếu."""
    if not text:
        return None
    hits = _digit_runs_12(text)
    if hits:
        return hits[0]
    mixed = _fix_digit_tokens(text)
    hits = _digit_runs_12(mixed)
    if hits:
        return hits[0]
    real = sum(ch.isdigit() for ch in text)
    if real >= 10:
        for src in (mixed, text):
            collapsed = re.sub(r"\D", "", src)
            if len(collapsed) == 12:
                return collapsed
    if real < 8:
        return None
    mild = str.maketrans({
        "O": "0", "o": "0", "D": "0",
        "I": "1", "l": "1", "|": "1", "i": "1",
        "B": "8",
    })
    mapped = text.translate(mild)
    hits = _digit_runs_12(mapped)
    if hits:
        return hits[0]
    collapsed = re.sub(r"\D", "", mapped)
    return collapsed if len(collapsed) == 12 else None


def _id_birth_year(ident: str) -> Optional[int]:
    """Năm sinh mã hoá trong CCCD: số thứ 4 = thế kỷ+giới tính, 2 số sau = YY."""
    if len(ident) != 12 or not ident.isdigit() or ident[3] not in "012345":
        return None
    yy = int(ident[4:6])
    century = {"0": 1900, "1": 1900, "2": 2000, "3": 2000, "4": 2100, "5": 2100}[ident[3]]
    return century + yy


def _id_gender(ident: str) -> Optional[str]:
    if len(ident) != 12 or ident[3] not in "012345":
        return None
    return "Nam" if ident[3] in "024" else "Nữ"


def _id_structurally_ok(ident: str) -> bool:
    """Chỉ loại số CCCD trông như OCR bịa (toàn 0/1). Không chặn số lệch 1 chữ."""
    if not ident or len(ident) != 12 or not ident.isdigit():
        return False
    if len(set(ident)) <= 2:
        return False
    if sum(ch in "01" for ch in ident) >= 10:
        return False
    return True


def accept_id_number(text: Optional[str]) -> Optional[str]:
    ident = normalize_id_number(text or "")
    if ident and _id_structurally_ok(ident):
        return ident
    return None


def _id_score(ident: str, dob: Optional[str] = None, gender: Optional[str] = None) -> float:
    if not _id_structurally_ok(ident):
        return -1000.0
    score = 10.0
    if ident[:3] in _CCCD_PROVINCE:
        score += 8.0
    uniq = len(set(ident))
    if uniq >= 5:
        score += 6.0
    elif uniq == 3:
        score -= 6.0
    max_run = max(len(match.group(0)) for match in re.finditer(r"(.)\1*", ident))
    if max_run >= 5:
        score -= 12.0
    year = _id_birth_year(ident)
    if dob:
        try:
            birth = int(dob.split("/")[2])
        except (IndexError, ValueError, AttributeError):
            birth = None
        if birth is not None and year is not None:
            score += 28.0 if year == birth else -22.0
    if gender in ("Nam", "Nữ"):
        encoded = _id_gender(ident)
        if encoded == gender:
            score += 18.0
        elif encoded:
            score -= 18.0
    return score


def prefer_id(
    old: Optional[str],
    new: Optional[str],
    dob: Optional[str] = None,
    gender: Optional[str] = None,
) -> Optional[str]:
    """Giữ số CCCD đã hợp lệ; không để frame nhiễu (001000000111) ghi đè."""
    old_ok = accept_id_number(old)
    new_ok = accept_id_number(new)
    if not new_ok:
        return old_ok
    if not old_ok:
        return new_ok
    if old_ok == new_ok:
        return old_ok
    if _id_score(new_ok, dob, gender) > _id_score(old_ok, dob, gender) + 15:
        return new_ok
    return old_ok


def normalize_dob(text: str) -> Optional[str]:
    """Chuẩn hoá DD/MM/YYYY từ ROI ngày sinh."""
    return pick_dob(text or "")


def normalize_gender(text: str) -> Optional[str]:
    """Chỉ nhận Nam hoặc Nữ. Không lấy 'Nam' từ Việt Nam / Nam Định."""
    raw = (text or "").strip()
    if not raw:
        return None
    if re.search(r"[nN][ữỮ]", raw):
        return "Nữ"
    return _find_sex_in_text(fold(raw))


def _strip_name_label(line: str) -> str:
    """Tách phần tên nằm cùng dòng với nhãn kể cả khi OCR bỏ sót dấu hai chấm ':'."""
    if ":" in line:
        after_colon = line.split(":")[-1].strip()
        if after_colon:
            return after_colon
    f = fold(line)
    m = _INLINE_NAME_PREFIX_RE.match(f)
    if m and m.end() < len(line):
        return line[m.end():].strip(" :.-/")
    return ""


def _valid_date(d: int, m: int, y: int) -> Optional[str]:
    try:
        dt = date(y, m, d)
    except ValueError:
        return None
    if not (1920 <= y <= date.today().year):
        return None
    return dt.strftime("%d/%m/%Y")


def _extract_dates_in_line(line: str, allow_flex: Optional[bool] = None) -> List[Tuple[int, str]]:
    """Tìm mọi ngày hợp lệ (năm, 'dd/mm/yyyy') trong 1 dòng, kể cả khi dấu '/' hoặc ':' bị nhiễu."""
    # Bỏ qua nếu dòng chứa số CCCD 12 số trùng khớp hoàn toàn mà không có ngày khác
    norm_line = _fix_digit_tokens(line)
    # Xóa tạm chuỗi 12 số CCCD (nếu có trên cùng dòng) để không cắt nhầm 8 số cuối của CCCD thành ngày
    norm_no_id = _ID_RE.sub(" ", norm_line)
    folded = fold(line)
    labeled = bool(_DOB_LABEL_RE.search(folded))
    compact = re.sub(r"\D", "", norm_no_id)
    if allow_flex is None:
        allow_flex = labeled or bool(re.search(r"(?<!\d)\d{8,10}(?!\d)", compact))

    found: List[Tuple[int, str]] = []
    regexes = [_DATE_SEP_RE, _DATE_SPACE_RE]
    if allow_flex:
        regexes.append(_DATE_FLEX_RE)
    for regex in regexes:
        for m in regex.finditer(norm_no_id):
            d_str, m_str, y_str = m.group(1), m.group(2), m.group(3)
            val = _valid_date(int(d_str), int(m_str), int(y_str))
            if val and all(v != val for _, v in found):
                found.append((int(y_str), val))
        if found:
            break
    return found


def _dob_line_score(text: str, year: int, value: str) -> float:
    folded = fold(text)
    score = 0.0
    if _EXPIRY_LINE_RE.search(folded):
        return -50.0
    if _DOB_LABEL_RE.search(folded):
        score += 40
    if "/" in value or "-" in (text or ""):
        score += 12
    today_y = date.today().year
    if year >= today_y:
        score -= 30
    elif year >= today_y - 2:
        score -= 8
    # Ngày sinh thường 16–80 tuổi
    age = today_y - year
    if 16 <= age <= 80:
        score += 8
    elif age < 10:
        score -= 20
    return score


def pick_dob(*texts: str) -> Optional[str]:
    ranked: List[Tuple[float, int, str]] = []
    for text in texts:
        if not text:
            continue
        if normalize_id_number(text) and not _DOB_LABEL_RE.search(fold(text)):
            continue
        for chunk in re.split(r"[\n|]+", text):
            if _EXPIRY_LINE_RE.search(fold(chunk)):
                continue
            for year, value in _extract_dates_in_line(chunk):
                ranked.append((_dob_line_score(chunk, year, value), year, value))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    return ranked[0][2]


def prefer_gender(old: Optional[str], new: Optional[str]) -> Optional[str]:
    """Nữ thắng Nam khi hai lần đọc lệch — lỗi phổ biến là dính 'Việt Nam'."""
    if new == "Nữ" or old == "Nữ":
        return "Nữ"
    return new or old or None


def prefer_dob(old: Optional[str], new: Optional[str]) -> Optional[str]:
    if not new:
        return old or None
    if not old:
        return new
    if old == new:
        return old
    today_y = date.today().year

    def year_of(val: str) -> int:
        try:
            return int(val.split("/")[2])
        except (IndexError, ValueError):
            return today_y

    old_y, new_y = year_of(old), year_of(new)
    old_bad = old_y >= today_y or old_y > today_y - 10
    new_bad = new_y >= today_y or new_y > today_y - 10
    if old_bad and not new_bad:
        return new
    if new_bad and not old_bad:
        return old
    return old


def _find_sex_in_text(text: str, locked_name_folded: str = "") -> Optional[str]:
    """Nhận diện Nam / Nữ từ chuỗi đã fold, chống nhầm 'Việt Nam' hoặc tên người dùng."""
    text = fold(text or "")
    if locked_name_folded:
        text = text.replace(locked_name_folded, " ")
    text = _VIET_NAM_RE.sub(" ", text)
    text = _PLACE_NAM_RE.sub(" ", text)
    text = _STOP_RE.split(text)[0]
    text = _ADDRESS_START_RE.split(text)[0]
    text = re.sub(r"\s+", " ", text).strip(" :./-")
    if not text:
        return None
    if _NU_TOKEN_RE.search(text):
        return "Nữ"
    if _NAM_TOKEN_RE.search(text):
        return "Nam"
    return None


# -----------------------------------------------------------------------------
# Trích xuất trường thông tin từ các dòng văn bản (hỗ trợ khóa trường Pha 2)
# -----------------------------------------------------------------------------

def parse_cccd_lines(
    lines: List[str],
    known_fields: Optional[Dict[str, Optional[str]]] = None,
) -> Dict[str, Optional[str]]:
    """Trích xuất Số CCCD, Họ tên, Ngày sinh, Giới tính theo đúng thứ tự bố cục thẻ CCCD:

    Bố cục từ trên xuống dưới trên mặt trước thẻ CCCD:
      Tiêu đề ("CĂN CƯỚC CÔNG DÂN") -> Số CCCD (12 số) -> Họ và tên -> Ngày sinh -> Giới tính.
    Do đó Họ và tên LUÔN chỉ được tìm ở các dòng BÊN DƯỚI dòng Số CCCD.
    """
    known = known_fields or {}
    locked_id = accept_id_number((known.get("id_number") or "").strip())
    raw_locked_name = (known.get("full_name") or "").strip()
    locked_name = _clean_name(raw_locked_name) if raw_locked_name else None
    focus_lower = bool(locked_id and locked_name)

    lines = [re.sub(r"\s+", " ", ln).strip() for ln in lines if ln and ln.strip()]
    fixed = [_fix_digit_tokens(ln) for ln in lines]
    folded = [fold(ln) for ln in lines]

    result: Dict[str, Optional[str]] = {
        "id_number": locked_id,
        "full_name": locked_name,
        "dob": (known.get("dob") or "").strip() or None,
        "gender": (known.get("gender") or "").strip() or None,
    }

    # 1. Tìm dòng chứa Số CCCD 12 chữ số (dùng làm mốc: Họ tên bắt buộc nằm BÊN DƯỚI dòng này)
    id_line_idx: Optional[int] = None
    id_hits: List[Tuple[int, str]] = []
    for idx, ln in enumerate(fixed):
        raw = normalize_id_number(ln)
        if not raw:
            continue
        if id_line_idx is None:
            id_line_idx = idx
        cand = accept_id_number(raw)
        if cand:
            id_hits.append((idx, cand))
    if not result["id_number"] and id_hits:
        id_line_idx, result["id_number"] = max(
            id_hits, key=lambda item: (_id_score(item[1], result.get("dob"), result.get("gender")), -item[0])
        )
    elif result["id_number"] and id_hits:
        id_line_idx = id_hits[0][0]
    if not result["id_number"]:
        compact = " ".join(fixed)
        cand = accept_id_number(compact)
        if cand:
            result["id_number"] = cand
            for idx, ln in enumerate(fixed):
                digits = re.sub(r"\D", "", ln)
                if digits and digits in cand:
                    id_line_idx = idx
                    break

    # 2. Tìm Họ và tên (nếu chưa khóa): CHỈ xét các dòng bên dưới Số CCCD (idx > id_line_idx)
    name_line_idx: Optional[int] = None
    name_start_idx = (id_line_idx + 1) if id_line_idx is not None else 0

    if not result["full_name"]:
        for i in range(name_start_idx, len(folded)):
            if not _NAME_LABEL_RE.search(folded[i]):
                continue
            tail = _strip_name_label(lines[i])
            cands = [(i, tail)] if tail else []
            for offset in (1, 2):
                if i + offset < len(lines):
                    cands.append((i + offset, lines[i + offset]))
            for idx_cand, c in cands:
                c = c.strip()
                if c and _looks_like_name(c):
                    result["full_name"] = pretty_name(c) or draft_person_name(c) or _clean_name(c)
                    name_line_idx = idx_cand
                    break
            if result["full_name"]:
                break

    # Nếu đã có Họ tên (từ Pha 1 hoặc vừa tìm thấy), xác định vị trí dòng Họ tên để chỉ quét bên dưới
    locked_name_folded = fold(result["full_name"]) if result["full_name"] else ""
    if name_line_idx is None and locked_name_folded:
        for i, f in enumerate(folded):
            if locked_name_folded in f or _NAME_LABEL_RE.search(f):
                name_line_idx = i

    # Phạm vi dòng bắt đầu quét Ngày sinh & Giới tính (bên dưới Họ tên / Số CCCD)
    anchor_idx = name_line_idx if name_line_idx is not None else id_line_idx
    start_below_name = (anchor_idx + 1) if (anchor_idx is not None and anchor_idx + 1 < len(lines)) else 0

    # 3. Ngày sinh: ưu tiên dòng có nhãn Ngày sinh, sau đó quét mọi dòng bên dưới Họ tên (bỏ qua dòng hạn thẻ)
    dob_idx: Optional[int] = None
    if not result["dob"]:
        for i in range(start_below_name, len(folded)):
            if _DOB_LABEL_RE.search(folded[i]):
                for j in (i, i + 1):
                    if j < len(fixed) and not _EXPIRY_LINE_RE.search(folded[j]):
                        dates = _extract_dates_in_line(fixed[j])
                        if dates:
                            result["dob"], dob_idx = dates[0][1], j
                            break
                if result["dob"]:
                    break

    if not result["dob"]:
        candidates: List[Tuple[int, str, int]] = []
        search_range = range(start_below_name, len(fixed)) if (focus_lower or anchor_idx is not None) else range(len(fixed))
        for i in search_range:
            if _EXPIRY_LINE_RE.search(folded[i]):
                continue
            for yr, val in _extract_dates_in_line(fixed[i]):
                candidates.append((yr, val, i))
        if candidates:
            _, result["dob"], dob_idx = min(candidates)

    # Fallback tìm Họ tên: bắt buộc phải nằm DƯỚI dòng Số CCCD (id_line_idx < i < dob_idx)
    if not result["full_name"] and id_line_idx is not None:
        stop = dob_idx if dob_idx is not None else len(lines)
        for i in range(id_line_idx + 1, stop):
            if _looks_like_name(lines[i]):
                result["full_name"] = pretty_name(lines[i]) or draft_person_name(lines[i]) or _clean_name(lines[i])
                locked_name_folded = fold(result["full_name"])
                name_line_idx = i
                break

    # 4. Giới tính: tìm theo nhãn -> tìm quanh dòng Ngày sinh -> tìm mọi dòng bên dưới tên (trước Quê quán)
    if not result["gender"]:
        for i in range(start_below_name, len(folded)):
            m = _SEX_LABEL_RE.search(folded[i])
            if m:
                sex = _find_sex_in_text(folded[i][m.end():], locked_name_folded)
                if not sex and i + 1 < len(folded):
                    sex = _find_sex_in_text(folded[i + 1], locked_name_folded)
                if sex:
                    result["gender"] = sex
                    break

    if not result["gender"] and dob_idx is not None:
        for j in range(dob_idx, min(dob_idx + 3, len(folded))):
            if _ADDRESS_START_RE.search(folded[j]):
                break
            sex = _find_sex_in_text(folded[j], locked_name_folded)
            if sex:
                result["gender"] = sex
                break

    if not result["gender"]:
        for i in range(start_below_name, len(folded)):
            if name_line_idx is not None and i <= name_line_idx:
                continue
            if id_line_idx is not None and i <= id_line_idx:
                continue
            if _ADDRESS_START_RE.search(folded[i]):
                break
            if _NON_NAME_FUZZY_RE.search(folded[i]) and not _SEX_LABEL_RE.search(folded[i]):
                continue
            sex = _find_sex_in_text(folded[i], locked_name_folded)
            if sex:
                result["gender"] = sex
                break

    # Căn cước mới: nhãn Date of birth + Sex cùng hàng, giá trị nằm hàng dưới.
    if not result["dob"] or not result["gender"]:
        for i, folded_line in enumerate(folded):
            if not (_DOB_LABEL_RE.search(folded_line) and _SEX_LABEL_RE.search(folded_line)):
                continue
            for j in (i + 1, i + 2):
                if j >= len(lines):
                    break
                if _ADDRESS_START_RE.search(folded[j]) or _EXPIRY_LINE_RE.search(folded[j]):
                    break
                if not result["dob"]:
                    dates = _extract_dates_in_line(fixed[j])
                    if dates:
                        result["dob"] = dates[0][1]
                        dob_idx = j
                if not result["gender"]:
                    sex = _find_sex_in_text(folded[j], locked_name_folded)
                    if sex:
                        result["gender"] = sex
            break

    return result


def is_id_card_text(lines: List[str]) -> bool:
    joined = fold(" ".join(lines))
    return any(k in joined for k in _CARD_KEYWORDS)


# -----------------------------------------------------------------------------
# Thị giác máy tính: định vị thẻ, tiền xử lý & đánh giá chất lượng
# -----------------------------------------------------------------------------

def _order_quad(pts: np.ndarray) -> np.ndarray:
    pts = pts.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype=np.float32)


def locate_card(img_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Tìm tứ giác thẻ trong ảnh. Trả về 4 đỉnh (TL, TR, BR, BL) theo toạ độ ảnh gốc hoặc None."""
    h, w = img_bgr.shape[:2]
    scale = 640.0 / max(w, h)
    small = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 25, 100)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area_img = small.shape[0] * small.shape[1]

    for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        area = cv2.contourArea(cnt)
        if area < 0.22 * area_img:
            break
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            quad = _order_quad(approx)
        else:
            rect = cv2.minAreaRect(cnt)
            rw, rh = rect[1]
            if rw * rh <= 0 or area / (rw * rh) < 0.85:
                continue
            quad = _order_quad(cv2.boxPoints(rect))
        wtop = np.linalg.norm(quad[1] - quad[0])
        hleft = np.linalg.norm(quad[3] - quad[0])
        if hleft < 1:
            continue
        ratio = max(wtop, hleft) / min(wtop, hleft)
        if 1.30 <= ratio <= 1.90:
            return quad / scale
    return None


def warp_card(img_bgr: np.ndarray, quad: np.ndarray) -> np.ndarray:
    wtop = np.linalg.norm(quad[1] - quad[0])
    hleft = np.linalg.norm(quad[3] - quad[0])
    if hleft > wtop:  # Thẻ đang dựng đứng -> xoay đỉnh để luôn ra ảnh nằm ngang
        quad = np.roll(quad, -1, axis=0)
    dst = np.array([[0, 0], [WARP_W - 1, 0], [WARP_W - 1, WARP_H - 1], [0, WARP_H - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(quad.astype(np.float32), dst)
    return cv2.warpPerspective(img_bgr, M, (WARP_W, WARP_H), flags=cv2.INTER_CUBIC)


def deskew_and_crop(img_bgr: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Bước 1: 4 góc thẻ + warpPerspective về khổ chuẩn. Không thấy góc thì scale cả khung."""
    height, width = img_bgr.shape[:2]
    already_card = 1.40 <= (width / float(max(1, height))) <= 1.75
    quad = locate_card(img_bgr)
    if quad is not None:
        area = float(cv2.contourArea(quad.astype(np.float32)))
        frac = area / float(max(1, width * height))
        # Guide crop đã gần bằng thẻ: đừng warp nhầm ảnh chân dung / hoa văn bên trong.
        if already_card and frac < 0.62:
            quad = None
        elif 0.28 <= frac <= 0.98:
            return warp_card(img_bgr, quad), quad
    warped = cv2.resize(img_bgr, (WARP_W, WARP_H), interpolation=cv2.INTER_CUBIC)
    return warped, None


def crop_chip_rois(warped: np.ndarray, layout: str = "old") -> Dict[str, np.ndarray]:
    """Bước 2: cắt 5 ROI. layout=old: CCCD chip 2021; layout=new: Căn cước 2024."""
    table = CHIP_ROIS_NEW if layout == "new" else CHIP_ROIS
    height, width = warped.shape[:2]
    rois: Dict[str, np.ndarray] = {}
    for key, (x0, y0, x1, y1) in table.items():
        xa = int(max(0, min(width - 1, round(x0 * width))))
        xb = int(max(xa + 1, min(width, round(x1 * width))))
        ya = int(max(0, min(height - 1, round(y0 * height))))
        yb = int(max(ya + 1, min(height, round(y1 * height))))
        rois[key] = warped[ya:yb, xa:xb]
    id_bottom = table["id_number"][3]
    dob_top = table["dob"][1]
    xa = int(round(0.26 * width))
    ya = int(round(max(0.0, id_bottom - 0.02) * height))
    yb = int(round(min(1.0, dob_top + 0.04) * height))
    if yb - ya >= 8:
        rois["full_name"] = warped[ya:yb, xa:]
    return rois


def name_between_id_and_dob(lines: List[str]) -> Optional[str]:
    """Họ tên: sau Số CCCD / nhãn Họ và tên, trước Ngày sinh — không lấy quê quán."""
    id_idx: Optional[int] = None
    label_idx: Optional[int] = None
    stop = len(lines)
    for idx, line in enumerate(lines):
        folded = fold(line)
        if id_idx is None and normalize_id_number(line):
            id_idx = idx
            continue
        if id_idx is not None and idx <= id_idx:
            continue
        if label_idx is None and _NAME_LABEL_RE.search(folded):
            label_idx = idx
        if pick_dob(line) and (id_idx is None or idx > id_idx):
            stop = idx
            break
        if _SEX_LABEL_RE.search(folded) or _ADDRESS_START_RE.search(folded) or _STOP_RE.search(folded):
            stop = idx
            break
        if _is_address_text(line) and not _NAME_LABEL_RE.search(folded):
            stop = idx
            break
    start = label_idx if label_idx is not None else ((id_idx + 1) if id_idx is not None else 0)
    if start >= stop:
        return None
    return pick_name(*lines[start:stop])


def enhance_roi(img_bgr: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """Tăng tương phản nhẹ từng ROI, không đụng toàn ảnh."""
    if img_bgr is None or img_bgr.size == 0:
        return img_bgr
    height, width = img_bgr.shape[:2]
    if height < 18:
        scale = 32.0 / max(1, height)
        img_bgr = cv2.resize(
            img_bgr,
            (max(8, int(round(width * scale))), 32),
            interpolation=cv2.INTER_CUBIC,
        )
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    luma, a_ch, b_ch = cv2.split(lab)
    luma = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(luma)
    return cv2.cvtColor(cv2.merge((luma, a_ch, b_ch)), cv2.COLOR_LAB2BGR)


def line_strips(img_bgr: np.ndarray, max_lines: int = 3) -> List[np.ndarray]:
    """Tách ROI nhiều dòng thành dải 1 dòng — VietOCR chỉ đọc được một hàng chữ."""
    if img_bgr is None or img_bgr.size == 0:
        return []
    height, width = img_bgr.shape[:2]
    if height < 12 or width < 12:
        return [img_bgr]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    if float(gray.mean()) < 115:
        gray = cv2.bitwise_not(gray)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    bw = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 21, 8
    )
    ink = (bw > 0).sum(axis=1).astype(np.float32)
    peak = float(ink.max()) if ink.size else 0.0
    if peak < max(4.0, width * 0.015):
        return [img_bgr]
    mask = ink >= max(peak * 0.16, 3.0)
    strips: List[np.ndarray] = []
    row = 0
    while row < height:
        if not mask[row]:
            row += 1
            continue
        end = row
        while end < height and mask[end]:
            end += 1
        if end - row >= max(5, height // 14):
            pad = max(1, (end - row) // 5)
            y0 = max(0, row - pad)
            y1 = min(height, end + pad)
            strips.append(img_bgr[y0:y1, :])
        row = end
    if not strips:
        return [img_bgr]
    return strips[:max_lines]


def tight_line_crops(img_bgr: np.ndarray, max_lines: int = 4) -> List[np.ndarray]:
    """Chỉ giữ dải mỏng 1 hàng chữ. Ảnh cao (nhãn+tên chồng) bị loại — tránh OCR tầm bậy."""
    if img_bgr is None or img_bgr.size == 0:
        return []
    height, width = img_bgr.shape[:2]
    max_h = max(42, int(width * 0.26))
    out: List[np.ndarray] = []
    for strip in line_strips(img_bgr, max_lines=max_lines):
        sh, sw = strip.shape[:2]
        if sh < 6 or sw < 20:
            continue
        if sh > max_h:
            continue
        out.append(strip)
    if out:
        return out
    y0 = int(height * 0.48)
    bottom = img_bgr[y0:, :]
    return [bottom] if bottom.size else [img_bgr]


def word_crops(img_bgr: np.ndarray, max_words: int = 6) -> List[np.ndarray]:
    """Tách từng tiếng trên một hàng tên — OCR từng ô, không cắt chữ cuối."""
    if img_bgr is None or img_bgr.size == 0:
        return []
    height, width = img_bgr.shape[:2]
    if height < 8 or width < 20:
        return [img_bgr]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    if float(gray.mean()) < 115:
        gray = cv2.bitwise_not(gray)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    bw = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 21, 8
    )
    kx = max(3, height // 5)
    ky = max(2, height // 6)
    closed = cv2.morphologyEx(
        bw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (kx, ky))
    )
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: List[Tuple[int, int, int, int]] = []
    min_h = max(7, int(height * 0.28))
    for cnt in contours:
        x, y, bw_, bh = cv2.boundingRect(cnt)
        if bh < min_h or bw_ < 3:
            continue
        if bw_ > width * 0.92:
            continue
        boxes.append((x, y, bw_, bh))
    boxes.sort(key=lambda item: item[0])
    merged: List[Tuple[int, int, int, int]] = []
    for x, y, bw_, bh in boxes:
        if merged:
            px, py, pw, ph = merged[-1]
            gap = x - (px + pw)
            same_row = abs((y + bh / 2.0) - (py + ph / 2.0)) < 0.55 * max(bh, ph)
            if same_row and gap <= max(4, height // 3):
                x1 = max(px + pw, x + bw_)
                y0 = min(py, y)
                y1 = max(py + ph, y + bh)
                merged[-1] = (px, y0, x1 - px, y1 - y0)
                continue
        merged.append((x, y, bw_, bh))
    crops: List[np.ndarray] = []
    for x, y, bw_, bh in merged[:max_words]:
        pad_x = max(1, bw_ // 12)
        pad_y = max(1, bh // 6)
        x0 = max(0, x - pad_x)
        y0 = max(0, y - pad_y)
        x1 = min(width, x + bw_ + pad_x)
        y1 = min(height, y + bh + pad_y)
        piece = img_bgr[y0:y1, x0:x1]
        if piece.size:
            crops.append(piece)
    return crops


def prepare_ocr_line(img_bgr: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """Pad nhẹ, ít CLAHE — giữ nét chữ, không làm méo hàng."""
    if img_bgr is None or img_bgr.size == 0:
        return img_bgr
    height, width = img_bgr.shape[:2]
    pad = max(2, height // 8)
    img_bgr = cv2.copyMakeBorder(img_bgr, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    luma, a_ch, b_ch = cv2.split(lab)
    luma = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(8, 8)).apply(luma)
    return cv2.cvtColor(cv2.merge((luma, a_ch, b_ch)), cv2.COLOR_LAB2BGR)


def _ink_enough(img_bgr: np.ndarray) -> bool:
    if img_bgr is None or img_bgr.size == 0:
        return False
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var()) >= 6.0


def fields_from_roi_texts(raw: Dict[str, str]) -> Dict[str, Optional[str]]:
    """Bước 4: regex / sửa lỗi quang học từng trường. Không trộn ID vào tên/ngày sinh."""
    name_bits = raw.get("full_name") or ""
    dob_bits = raw.get("dob") or ""
    lower = raw.get("lower_row") or ""
    sex = raw.get("sex") or ""
    ident = raw.get("id_number") or ""
    picked = pick_name(name_bits)
    name = valid_person_name(picked) or draft_person_name(picked)
    dob = pick_dob(dob_bits, lower)
    gender = prefer_gender(normalize_gender(sex), normalize_gender(lower))
    if not name or not dob or not gender:
        parsed = parse_cccd_lines(
            [part for part in (ident, name_bits, dob_bits, sex, lower) if part]
        )
        name = name or parsed.get("full_name")
        dob = dob or parsed.get("dob")
        gender = prefer_gender(gender, parsed.get("gender"))
    return {
        "id_number": accept_id_number(ident),
        "full_name": name,
        "dob": dob,
        "gender": gender,
    }


def _merge_fields(
    primary: Dict[str, Optional[str]],
    secondary: Dict[str, Optional[str]],
) -> Dict[str, Optional[str]]:
    out = dict(primary)
    for key in FIELDS:
        if not out.get(key) and secondary.get(key):
            out[key] = secondary[key]
    return out


def assess_quality(img_bgr: np.ndarray, relaxed: bool = False) -> Dict[str, Any]:
    h, w = img_bgr.shape[:2]
    scale = 640.0 / max(w, h)
    gray = cv2.cvtColor(cv2.resize(img_bgr, (int(w * scale), int(h * scale))), cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    glare = float((gray >= 250).mean())
    edges = cv2.Canny(gray, 60, 160)
    edge_density = float((edges > 0).mean())

    min_sharp = MIN_SHARPNESS_ZOOM if relaxed else MIN_SHARPNESS
    max_glare = 0.18 if relaxed else MAX_GLARE_RATIO

    issue = None
    if brightness < MIN_BRIGHTNESS:
        issue = "Ảnh quá tối, vui lòng tăng ánh sáng"
    elif brightness > MAX_BRIGHTNESS:
        issue = "Ảnh quá sáng, vui lòng giảm ánh sáng"
    elif glare > max_glare:
        issue = "Thẻ bị lóa sáng, hãy nghiêng nhẹ thẻ để tránh phản quang"
    elif sharpness < min_sharp:
        issue = "Ảnh hơi mờ, giữ yên hoặc đưa gần vùng Ngày sinh & Giới tính"
    return {
        "ok": issue is None,
        "issue": issue,
        "brightness": round(brightness, 1),
        "sharpness": round(sharpness, 1),
        "glare_ratio": round(glare, 4),
        "edge_density": round(edge_density, 4),
    }


def _crush_highlights(img_bgr: np.ndarray) -> np.ndarray:
    """Nén vùng cháy sáng trước khi đánh giá chất lượng / OCR."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    lf = l_ch.astype(np.float32)
    over = np.maximum(lf - 220.0, 0.0)
    l_ch = np.clip(lf - over * 0.40, 0, 255).astype(np.uint8)
    return cv2.cvtColor(cv2.merge((l_ch, a_ch, b_ch)), cv2.COLOR_LAB2BGR)


def _fit_ocr(img_bgr: np.ndarray, max_w: int = OCR_MAX_W) -> np.ndarray:
    height, width = img_bgr.shape[:2]
    if width <= max_w:
        return img_bgr
    scale = max_w / float(width)
    return cv2.resize(
        img_bgr,
        (max_w, max(1, int(round(height * scale)))),
        interpolation=cv2.INTER_AREA,
    )


def _lighting_issue(issue: Optional[str]) -> bool:
    if not issue:
        return False
    return any(token in issue for token in ("quá sáng", "lóa", "quá tối"))


def _preprocess_for_ocr(img_bgr: np.ndarray, sharpen: bool = False) -> np.ndarray:
    """Tăng tương phản nhẹ CLAHE (tránh làm nổi hoa văn chìm của thẻ) và làm nét chữ nhỏ."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.2 if sharpen else 1.8, tileGridSize=(8, 8))
    l_ch = clahe.apply(l_ch)
    enhanced = cv2.cvtColor(cv2.merge((l_ch, a_ch, b_ch)), cv2.COLOR_LAB2BGR)
    if sharpen:
        blur = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.0)
        enhanced = cv2.addWeighted(enhanced, 1.35, blur, -0.35, 0)
    return cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)


def _merge_line_boxes(boxes: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
    if not boxes:
        return boxes
    merged: List[Tuple[int, int, int, int]] = []
    for x, y, w, h in boxes:
        if merged:
            px, py, pw, ph = merged[-1]
            same_row = abs((y + h / 2.0) - (py + ph / 2.0)) < 0.55 * max(h, ph)
            close = x <= px + pw + max(10, int(0.8 * max(h, ph)))
            if same_row and close:
                x1 = max(px + pw, x + w)
                y0 = min(py, y)
                y1 = max(py + ph, y + h)
                merged[-1] = (px, y0, x1 - px, y1 - y0)
                continue
        merged.append((x, y, w, h))
    return merged


def _detect_line_boxes(img_bgr: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Tách dòng chữ trên CCCD bằng morphology — nhanh, không dùng CRAFT."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    bw = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 21, 10
    )
    kx = max(15, width // 22)
    ky = max(2, height // 90)
    closed = cv2.morphologyEx(
        bw, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (kx, ky))
    )
    closed = cv2.dilate(closed, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 2)), iterations=1)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_h = max(8, height // 45)
    max_h = max(min_h + 1, height // 4)
    boxes: List[Tuple[int, int, int, int]] = []
    for cnt in contours:
        x, y, bw_, bh = cv2.boundingRect(cnt)
        if bh < min_h or bh > max_h or bw_ < min_h * 2:
            continue
        if bw_ / float(bh) < 1.35:
            continue
        if bw_ > width * 0.98:
            continue
        pad_x = max(2, bw_ // 30)
        pad_y = max(2, bh // 8)
        x0 = max(0, x - pad_x)
        y0 = max(0, y - pad_y)
        x1 = min(width, x + bw_ + pad_x)
        y1 = min(height, y + bh + pad_y)
        boxes.append((x0, y0, x1 - x0, y1 - y0))
    boxes.sort(key=lambda b: (b[1], b[0]))
    boxes = _merge_line_boxes(boxes)
    picked = _priority_boxes(img_bgr, boxes)
    if len(picked) >= 3:
        return picked
    return _layout_strips(img_bgr)


def _priority_boxes(
    img_bgr: np.ndarray,
    boxes: List[Tuple[int, int, int, int]],
) -> List[Tuple[int, int, int, int]]:
    """Bỏ tiêu đề trên cùng; giữ số CCCD và các dòng từ Họ tên xuống Date of Birth / Sex."""
    height, width = img_bgr.shape[:2]
    left = int(width * 0.18)
    kept: List[Tuple[int, int, int, int]] = []
    for x, y, bw, bh in boxes:
        cy = y + bh / 2.0
        if cy < height * 0.14 or cy > height * 0.84:
            continue
        if x + bw < left and bw < width * 0.35:
            continue
        kept.append((x, y, bw, bh))
    return kept[:6]


def _layout_strips(img_bgr: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """3 dải phải: Số CCCD, Họ tên, rồi từ tên xuống Ngày sinh/Giới tính."""
    height, width = img_bgr.shape[:2]
    left = int(width * 0.22)
    rw = max(16, width - left)
    return [
        (left, int(height * 0.18), rw, max(8, int(height * 0.22))),
        (left, int(height * 0.38), rw, max(8, int(height * 0.18))),
        (left, int(height * 0.52), rw, max(8, int(height * 0.26))),
    ]


def _band_boxes(img_bgr: np.ndarray, bands: int = 6) -> List[Tuple[int, int, int, int]]:
    """Fallback: cắt ngang thẻ thành dải — luôn có vùng chữ dù morphology fail."""
    height, width = img_bgr.shape[:2]
    out: List[Tuple[int, int, int, int]] = []
    for i in range(bands):
        y0 = max(0, int(height * i / bands) - 2)
        y1 = min(height, int(height * (i + 1) / bands) + 2)
        if y1 - y0 >= 8:
            out.append((0, y0, width, y1 - y0))
    return out


def group_lines(results: List[Tuple[Any, str, float]], min_conf: float = 0.04) -> List[str]:
    """Gom các box chữ thành dòng theo thứ tự đọc (trên->dưới, trái->phải)."""
    items = []
    for box, text, conf in results:
        if conf < min_conf or not text.strip():
            continue
        pts = np.array(box, dtype=np.float32)
        y0, y1 = pts[:, 1].min(), pts[:, 1].max()
        items.append({"yc": (y0 + y1) / 2, "h": max(1.0, y1 - y0), "x": pts[:, 0].min(), "text": text.strip()})
    if not items:
        return []
    items.sort(key=lambda it: it["yc"])
    med_h = float(np.median([it["h"] for it in items]))
    lines: List[List[dict]] = []
    for it in items:
        if lines and abs(it["yc"] - np.mean([x["yc"] for x in lines[-1]])) < 0.55 * med_h:
            lines[-1].append(it)
        else:
            lines.append([it])
    return [" ".join(x["text"] for x in sorted(ln, key=lambda x: x["x"])) for ln in lines]


def _build_vietocr():
    """Nạp VietOCR offline trên CPU, không giữ lock của engine."""
    import sys
    import yaml
    import torch

    venv_site = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".venv", "Lib", "site-packages"))
    if os.path.isdir(venv_site) and venv_site not in sys.path:
        sys.path.append(venv_site)
    from vietocr.tool.config import Cfg
    from vietocr.tool.predictor import Predictor

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    torch.set_num_threads(1)
    base_path = os.path.join(_VIETOCR_DIR, "base.yml")
    seq_path = os.path.join(_VIETOCR_DIR, "vgg-seq2seq.yml")
    weights = os.path.abspath(os.path.join(_VIETOCR_DIR, "vgg_seq2seq.pth"))
    if not os.path.isfile(weights):
        raise FileNotFoundError(f"Thiếu file trọng số: {weights}")
    with open(base_path, encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    with open(seq_path, encoding="utf-8") as handle:
        cfg.update(yaml.safe_load(handle) or {})
    cnn = dict(cfg.get("cnn") or {})
    cnn["pretrained"] = False
    cfg["cnn"] = cnn
    cfg["weights"] = weights
    cfg["device"] = "cpu"
    cfg["quiet"] = True
    cfg["predictor"] = dict(cfg.get("predictor") or {}, beamsearch=False)
    return Predictor(Cfg(cfg))


# -----------------------------------------------------------------------------
# Động cơ OCR (singleton, nạp lười trong luồng nền)
# -----------------------------------------------------------------------------

class IdCardOCREngine:
    def __init__(self) -> None:
        self._reader = None
        self._onnx = None
        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()
        self._loading = False
        self._error: Optional[str] = None

    @property
    def ready(self) -> bool:
        return self._onnx is not None or self._reader is not None

    def status(self) -> Dict[str, Any]:
        return {"ready": self.ready, "loading": self._loading, "error": self._error}

    def _load(self) -> None:
        if self._onnx is not None or self._reader is not None:
            return
        if not self._load_lock.acquire(blocking=False):
            return
        self._loading = True
        self._error = None
        try:
            from vietocr_onnx import VietOcrOnnx, onnx_files_present

            if onnx_files_present():
                recognizer = VietOcrOnnx()
                recognizer.warmup()
                self._onnx = recognizer
            else:
                self._reader = _build_vietocr()
        except Exception as exc:  # pragma: no cover - phụ thuộc môi trường
            self._onnx = None
            try:
                self._reader = _build_vietocr()
            except Exception:
                self._reader = None
                self._error = f"Không thể nạp VietOCR: {exc}"
        finally:
            self._loading = False
            self._load_lock.release()

    def warmup_async(self) -> None:
        if self.ready or self._loading:
            return
        threading.Thread(target=self._load, name="vietocr-warmup", daemon=True).start()

    def read_lines(self, img_bgr: np.ndarray, sensitive: bool = False) -> List[str]:
        from PIL import Image

        boxes = _detect_line_boxes(img_bgr)
        if not boxes:
            return []
        crops = []
        meta = []
        for x, y, w, h in boxes:
            crop = img_bgr[y : y + h, x : x + w]
            if crop.size == 0:
                continue
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            crops.append(Image.fromarray(rgb))
            meta.append((x, y, w, h))
        if not crops:
            return []
        with self._infer_lock:
            texts = self._reader.predict_batch(crops)
        results = []
        for (x, y, w, h), text in zip(meta, texts):
            line = str(text or "").strip()
            if not line:
                continue
            box = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
            results.append((box, line, 1.0))
        return group_lines(results, min_conf=0.0)

    def _read_lines_compat(self, img_bgr: np.ndarray, sensitive: bool = False) -> List[str]:
        """Gọi read_lines tương thích ngược với monkeypatch trong unit test (1 tham số)."""
        try:
            return self.read_lines(img_bgr, sensitive=sensitive)
        except TypeError:
            return self.read_lines(img_bgr)

    def _ocr_name_crop(self, crop: Optional[np.ndarray]) -> str:
        """OCR từng tiếng trên dòng tên rồi ghép — không để VietOCR nuốt chữ cuối."""
        if crop is None or crop.size == 0:
            return ""
        parts: List[str] = []
        for strip in tight_line_crops(crop, max_lines=2):
            if not _ink_enough(strip):
                continue
            blobs = word_crops(strip)
            if len(blobs) >= 2:
                bits: List[str] = []
                for blob in blobs[:4]:
                    piece = prepare_ocr_line(blob)
                    if piece is None or piece.size == 0:
                        continue
                    token = (self._onnx.predict(piece, max_len=12, max_width=220) or "").strip()
                    first = token.split()[0] if token else ""
                    if not first or not _vn_name_syllable(first) or _is_name_junk(first):
                        if bits:
                            break
                        continue
                    bits.append(first)
                if bits:
                    parts.append(" ".join(bits))
                    continue
            enhanced = prepare_ocr_line(strip)
            if enhanced is None or enhanced.size == 0:
                continue
            text = self._onnx.predict(enhanced, max_len=28, max_width=800)
            if text:
                parts.append(text)
        return "\n".join(parts)

    def _ocr_sex_crop(self, crop: Optional[np.ndarray]) -> str:
        """OCR từng tiếng trong ô giới tính — tránh VietOCR nuốt 'Nữ' vì 'Việt Nam'."""
        if crop is None or crop.size == 0:
            return ""
        parts: List[str] = []
        strips = line_strips(crop, max_lines=2)
        if not strips:
            strips = [crop]
        for strip in strips:
            if not _ink_enough(strip):
                continue
            blobs = word_crops(strip, max_words=8)
            got = False
            if blobs:
                bits: List[str] = []
                for blob in blobs[:8]:
                    piece = prepare_ocr_line(blob)
                    if piece is None or piece.size == 0:
                        continue
                    token = self._onnx.predict(piece, max_len=10, max_width=160)
                    if token:
                        bits.append(token)
                if bits:
                    parts.append(" ".join(bits))
                    got = True
            if got:
                continue
            enhanced = prepare_ocr_line(strip)
            if enhanced is None or enhanced.size == 0:
                continue
            text = self._onnx.predict(
                enhanced, max_len=ROI_MAX_LEN["sex"], max_width=ROI_MAX_WIDTH["sex"]
            )
            if text:
                parts.append(text)
        if parts:
            return " ".join(parts)
        enhanced = prepare_ocr_line(crop)
        if enhanced is None or enhanced.size == 0:
            return ""
        return self._onnx.predict(
            enhanced, max_len=ROI_MAX_LEN["sex"], max_width=ROI_MAX_WIDTH["sex"]
        )

    def _ocr_crop(self, crop: Optional[np.ndarray], max_len: int, max_width: int, max_lines: int = 3) -> str:
        if crop is None or crop.size == 0:
            return ""
        parts: List[str] = []
        for strip in line_strips(crop, max_lines=max_lines):
            if not _ink_enough(strip):
                continue
            enhanced = enhance_roi(strip)
            if enhanced is None or enhanced.size == 0:
                continue
            text = self._onnx.predict(enhanced, max_len=max_len, max_width=max_width)
            if text:
                parts.append(text)
        if parts:
            return "\n".join(parts)
        enhanced = enhance_roi(crop)
        if enhanced is None or enhanced.size == 0:
            return ""
        return self._onnx.predict(enhanced, max_len=max_len, max_width=max_width)

    def _predict_rois(self, rois: Dict[str, np.ndarray], keys: Tuple[str, ...]) -> Dict[str, str]:
        raw: Dict[str, str] = {}
        for key in keys:
            if key == "full_name":
                raw[key] = self._ocr_name_crop(rois.get(key))
                continue
            if key == "sex":
                raw[key] = self._ocr_sex_crop(rois.get(key))
                continue
            raw[key] = self._ocr_crop(
                rois.get(key),
                max_len=ROI_MAX_LEN.get(key, 24),
                max_width=ROI_MAX_WIDTH.get(key, 320),
                max_lines=3 if key == "lower_row" else 2,
            )
        return raw

    def _read_panel_lines(self, warped: np.ndarray) -> List[str]:
        height, width = warped.shape[:2]
        panel = warped[int(height * 0.16) : int(height * 0.84), int(width * 0.26) :]
        if panel.size == 0:
            return []
        lines: List[str] = []
        strips = line_strips(panel, max_lines=10)
        sources = strips if len(strips) >= 2 else []
        if not sources:
            for x, y, bw, bh in _detect_line_boxes(panel)[:8]:
                sources.append(panel[y : y + bh, x : x + bw])
        for crop in sources:
            text = self._ocr_crop(crop, max_len=40, max_width=512, max_lines=1)
            if text:
                lines.append(text)
        return lines

    def _scan_onnx(
        self,
        img_bgr: np.ndarray,
        resp: Dict[str, Any],
        focus_lower: bool,
    ) -> Dict[str, Any]:
        height, width = img_bgr.shape[:2]
        warped, quad = deskew_and_crop(img_bgr)
        if quad is not None:
            resp["card_detected"] = True
            resp["quad"] = [[round(float(x) / width, 4), round(float(y) / height, 4)] for x, y in quad]
        else:
            ratio = width / float(max(1, height))
            resp["card_detected"] = 1.25 <= ratio <= 2.05

        warped = _crush_highlights(warped)
        quality = assess_quality(warped, relaxed=True)
        resp["quality"] = quality
        lighting_bad = _lighting_issue(quality.get("issue"))

        rois = crop_chip_rois(warped)
        keys: Tuple[str, ...] = ("dob", "sex") if focus_lower else (
            "id_number",
            "full_name",
            "dob",
            "sex",
        )
        with self._infer_lock:
            raw = self._predict_rois(rois, keys)
            fields = fields_from_roi_texts(raw)
            if not fields.get("dob") or not fields.get("gender"):
                raw["lower_row"] = self._ocr_crop(
                    rois.get("lower_row"),
                    max_len=ROI_MAX_LEN["lower_row"],
                    max_width=ROI_MAX_WIDTH["lower_row"],
                    max_lines=3,
                )
                extra = fields_from_roi_texts(raw)
                fields["dob"] = fields.get("dob") or extra.get("dob")
                fields["gender"] = fields.get("gender") or extra.get("gender")
            weak_name = _is_incomplete_name(fields.get("full_name"))
            if (
                not fields.get("id_number")
                or weak_name
                or not fields.get("dob")
                or not fields.get("gender")
            ):
                rois_new = crop_chip_rois(warped, layout="new")
                alt_keys: Tuple[str, ...] = keys
                if fields.get("id_number") and not weak_name:
                    alt_keys = ("dob", "sex")
                raw_new = self._predict_rois(rois_new, alt_keys)
                if not fields.get("dob") or not fields.get("gender"):
                    raw_new["lower_row"] = self._ocr_crop(
                        rois_new.get("lower_row"),
                        max_len=ROI_MAX_LEN["lower_row"],
                        max_width=ROI_MAX_WIDTH["lower_row"],
                        max_lines=3,
                    )
                extra_new = fields_from_roi_texts(raw_new)
                fields["id_number"] = prefer_id(
                    fields.get("id_number"),
                    extra_new.get("id_number"),
                    fields.get("dob") or extra_new.get("dob"),
                    fields.get("gender") or extra_new.get("gender"),
                )
                if weak_name or not valid_person_name(fields.get("full_name")):
                    fields["full_name"] = (
                        prefer_name(fields.get("full_name"), extra_new.get("full_name"))
                        or extra_new.get("full_name")
                        or fields.get("full_name")
                    )
                fields["dob"] = prefer_dob(fields.get("dob"), extra_new.get("dob"))
                fields["gender"] = prefer_gender(fields.get("gender"), extra_new.get("gender"))
                raw.update({f"new_{k}": v for k, v in raw_new.items() if v})
            weak_name = _is_incomplete_name(fields.get("full_name"))
            weak_dob = not fields.get("dob")
            if not fields.get("id_number") or weak_name or weak_dob or not fields.get("gender"):
                panel_lines = self._read_panel_lines(warped)
                raw["panel"] = " | ".join(panel_lines)
                parsed = parse_cccd_lines(panel_lines)
                layout_raw = name_between_id_and_dob(panel_lines)
                layout_name = valid_person_name(layout_raw) or draft_person_name(layout_raw)
                parsed_name = valid_person_name(parsed.get("full_name")) or draft_person_name(
                    parsed.get("full_name")
                )
                fields["id_number"] = prefer_id(
                    fields.get("id_number"),
                    parsed.get("id_number"),
                    fields.get("dob") or parsed.get("dob"),
                    fields.get("gender") or parsed.get("gender"),
                )
                if weak_name or not valid_person_name(fields.get("full_name")):
                    fields["full_name"] = (
                        prefer_name(fields.get("full_name"), layout_name)
                        or prefer_name(fields.get("full_name"), parsed_name)
                        or valid_person_name(layout_name)
                        or valid_person_name(parsed_name)
                        or layout_name
                        or parsed_name
                        or fields.get("full_name")
                    )
                fields["dob"] = prefer_dob(fields.get("dob"), pick_dob(*panel_lines) or parsed.get("dob"))
                fields["gender"] = prefer_gender(fields.get("gender"), parsed.get("gender"))

        if focus_lower:
            fields["id_number"] = resp["fields"]["id_number"]
            fields["full_name"] = resp["fields"]["full_name"]
            fields["dob"] = fields["dob"] or resp["fields"].get("dob")
            fields["gender"] = fields["gender"] or resp["fields"].get("gender")

        resp["ocr_ran"] = True
        resp["roi_raw"] = raw
        resp["fields"] = fields
        resp["is_id_card"] = bool(
            fields.get("id_number")
            or fields.get("full_name")
            or fields.get("dob")
            or fields.get("gender")
            or is_id_card_text(list(raw.values()))
        )
        name_ok = bool(valid_person_name(fields.get("full_name")))
        resp["complete"] = bool(all(fields.get(k) for k in ("id_number", "dob", "gender")) and name_ok)
        if resp["complete"]:
            resp.update(guidance="Đã trích xuất đầy đủ thông tin CCCD!", color="green")
        elif lighting_bad and not resp["is_id_card"]:
            resp.update(guidance=quality["issue"], color="yellow")
        elif not resp["is_id_card"]:
            resp.update(guidance="Giữ thẻ trong khung, đang đọc mặt trước CCCD", color="cyan")
        else:
            missing = []
            if not fields.get("id_number"):
                missing.append("Số CCCD")
            if not draft_person_name(fields.get("full_name")):
                missing.append("Họ tên")
            if not fields.get("dob"):
                missing.append("Ngày sinh")
            if not fields.get("gender"):
                missing.append("Giới tính")
            if missing:
                resp.update(
                    guidance=f"Đang đọc, chưa rõ: {', '.join(missing)}. Giữ thẻ trong khung",
                    color="yellow",
                )
            else:
                resp.update(guidance="Đang đọc đủ họ tên. Giữ thẻ trong khung", color="yellow")
        return resp

    def _scan_legacy(
        self,
        img_bgr: np.ndarray,
        resp: Dict[str, Any],
        focus_lower: bool,
        locked_id: Optional[str],
        locked_name: Optional[str],
    ) -> Dict[str, Any]:
        h, w = img_bgr.shape[:2]
        quad = locate_card(img_bgr)
        if quad is not None:
            quad_area = float(cv2.contourArea(quad.astype(np.float32)))
            if quad_area >= 0.32 * (w * h):
                resp["card_detected"] = True
                resp["quad"] = [[round(float(x) / w, 4), round(float(y) / h, 4)] for x, y in quad]
                card = warp_card(img_bgr, quad)
            else:
                quad = None
                card = img_bgr
        else:
            card = img_bgr

        card = _crush_highlights(card)
        quality = assess_quality(card, relaxed=focus_lower)
        resp["quality"] = quality
        lighting_bad = _lighting_issue(quality.get("issue"))
        too_blurry = bool(quality.get("issue")) and "mờ" in (quality.get("issue") or "")

        if not focus_lower and quad is None and quality["edge_density"] < 0.016:
            resp.update(guidance="Chưa phát hiện thẻ. Đặt mặt trước CCCD vào khung chữ nhật", color="cyan")
            return resp
        if too_blurry and not lighting_bad:
            resp.update(guidance=quality["issue"], color="yellow")
            return resp

        card = _fit_ocr(card)
        lines = self._read_lines_compat(card, sensitive=False)
        fields = parse_cccd_lines(lines, known_fields=None if not focus_lower else resp["fields"])
        resp["ocr_ran"] = True
        resp["is_id_card"] = (
            is_id_card_text(lines)
            or bool(fields["id_number"])
            or bool(resp["card_detected"])
            or bool(fields["full_name"] and (fields["dob"] or fields["gender"]))
        )
        resp["fields"] = fields
        resp["focus_lower"] = bool(locked_id and locked_name)
        resp["complete"] = resp["is_id_card"] and all(fields.values())
        if resp["complete"]:
            resp.update(guidance="Đã trích xuất đầy đủ thông tin CCCD!", color="green")
        elif not resp["is_id_card"] and lighting_bad:
            resp.update(guidance=quality["issue"], color="yellow")
        elif not resp["is_id_card"]:
            resp.update(guidance="Giữ thẻ trong khung, đang đọc mặt trước CCCD", color="cyan")
        else:
            missing = [lbl for k, lbl in zip(FIELDS, ("Số CCCD", "Họ tên", "Ngày sinh", "Giới tính")) if not fields[k]]
            resp.update(guidance=f"Đang đọc, chưa rõ: {', '.join(missing)}. Giữ thẻ trong khung", color="yellow")
        return resp

    def scan(
        self,
        img_bgr: np.ndarray,
        known_fields: Optional[Dict[str, Optional[str]]] = None,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        known = known_fields or {}
        locked_id = (known.get("id_number") or "").strip() or None
        locked_name = (known.get("full_name") or "").strip() or None
        if locked_name and not _looks_like_name(locked_name):
            locked_name = None
        elif locked_name:
            locked_name = _clean_name(locked_name)
        focus_lower = bool(locked_id and locked_name)

        resp: Dict[str, Any] = {
            "ocr_ready": self.ready,
            "focus_lower": focus_lower,
            "card_detected": False,
            "quad": None,
            "quality": None,
            "ocr_ran": False,
            "is_id_card": focus_lower,
            "fields": {
                "id_number": locked_id,
                "full_name": locked_name,
                "dob": (known.get("dob") or "").strip() or None,
                "gender": (known.get("gender") or "").strip() or None,
            },
            "complete": False,
            "guidance": "",
            "color": "cyan",
        }

        if not self.ready:
            self.warmup_async()
            msg = self._error or "Đang tải mô hình OCR, vui lòng giữ thẻ trong khung"
            resp.update(guidance=msg, color="red" if self._error else "yellow")
        elif self._reader is not None:
            resp = self._scan_legacy(img_bgr, resp, focus_lower, locked_id, locked_name)
        else:
            resp = self._scan_onnx(img_bgr, resp, focus_lower)

        resp["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        return resp


engine = IdCardOCREngine()
