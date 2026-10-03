"""Minimal dependency-free PDF writer and best-effort text extractor."""
import re
import zlib

_W, _H, _M, _SIZE, _LEAD = 595, 842, 50, 11, 14
_PER_LINE = 90


def _lines(text):
    out = []
    for raw in text.replace("\r", "").split("\n"):
        raw = raw.expandtabs(4)
        while len(raw) > _PER_LINE:
            cut = raw.rfind(" ", 0, _PER_LINE)
            cut = cut if cut > 0 else _PER_LINE
            out.append(raw[:cut])
            raw = raw[cut:].lstrip()
        out.append(raw)
    return out


def _esc(s):
    s = s.encode("cp1252", "replace").decode("cp1252")
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_to_pdf(text):
    lines = _lines(text)
    per_page = (_H - 2 * _M) // _LEAD
    pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[]]
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", None,
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    kids = []
    for pg in pages:
        body = f"BT /F1 {_SIZE} Tf {_LEAD} TL {_M} {_H - _M} Td\n"
        body += "".join(f"({_esc(l)}) '\n" for l in pg) + "ET"
        data = body.encode("cp1252")
        objs.append(b"<< /Length %d >>\nstream\n" % len(data) + data + b"\nendstream")
        cid = len(objs)
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_W} {_H}] /Contents {cid} 0 R "
                    f"/Resources << /Font << /F1 3 0 R >> >> >>".encode())
        kids.append(f"{len(objs)} 0 R")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode()
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for o in offs:
        out += b"%010d 00000 n \n" % o
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
    return bytes(out)


_STR = rb"\((?:\\.|[^\\()])*\)"
_UNESC = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"", b"f": b""}


def _unescape(s):
    def rep(m):
        g = m.group(1)
        if g[:1].isdigit():
            return bytes([int(g, 8) & 255])
        return _UNESC.get(g, g)
    return re.sub(rb"\\([0-7]{1,3}|.)", rep, s[1:-1], flags=re.S).decode("cp1252", "replace")


def pdf_to_text(data):
    """Extract text from simple text-based PDFs (no OCR, no scanned images)."""
    if not data.startswith(b"%PDF"):
        raise ValueError("Not a PDF file.")
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        raw = m.group(1)
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            pass
        if b"BT" not in raw:
            continue
        for bt in re.finditer(rb"BT(.*?)ET", raw, re.S):
            for t in re.finditer(rb"(\[(?:" + _STR + rb"|[^\]()])*\])\s*TJ|(" + _STR + rb")\s*(?:Tj|'|\")"
                                 rb"|(T\*|Td|TD|T')", bt.group(1)):
                if t.group(1):
                    out.append("".join(_unescape(s) for s in re.findall(_STR, t.group(1))))
                elif t.group(2):
                    out.append(_unescape(t.group(2)))
                    if t.group(0).endswith((b"'", b'"')):
                        out.append("\n")
                else:
                    out.append("\n")
            out.append("\n")
    text = re.sub(r"\n{3,}", "\n\n", "".join(out)).strip()
    if not text:
        raise ValueError("No extractable text found in this PDF (scanned PDFs are not supported); paste the text instead.")
    return text
