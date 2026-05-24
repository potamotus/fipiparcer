"""MathML (от ФИПИ MathJax) → OMath (Office Math для Word)."""
from __future__ import annotations
import re
import mathml2omml


def fipi_mathml_to_omath(mathml: str) -> str:
    """Принять MathML с ФИПИ-префиксом 'm:' → отдать OMath XML.

    ФИПИ MathJax выдаёт:
        <m:math><m:mstyle><m:semantics><m:mrow>...
    mathml2omml ожидает без префикса:
        <math xmlns='...'><mstyle>...

    Возвращает строку OMath, готовую вставить в docx.
    """
    cleaned = mathml.replace("<m:", "<").replace("</m:", "</")
    # На случай xmlns:m=
    cleaned = re.sub(r'\sxmlns:m=', ' xmlns=', cleaned)
    # Если xmlns вообще нет — добавим (mathml2omml некоторые случаи без xmlns переваривает, но на всякий)
    if "xmlns=" not in cleaned:
        cleaned = cleaned.replace("<math", "<math xmlns='http://www.w3.org/1998/Math/MathML'", 1)
    return mathml2omml.convert(cleaned)
