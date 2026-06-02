"""
LaTeX 命令 → Unicode 字符映射
将常见 LaTeX 数学符号/格式命令替换为可读的 Unicode 文本。
"""
import re

# 单个命令替换表（长命令优先）
_LATEX_TO_UNI = {
    # 希腊字母小写
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
    r"\epsilon": "ε", r"\varepsilon": "ε", r"\zeta": "ζ", r"\eta": "η",
    r"\theta": "θ", r"\vartheta": "θ", r"\iota": "ι", r"\kappa": "κ",
    r"\lambda": "λ", r"\mu": "μ", r"\nu": "ν", r"\xi": "ξ",
    r"\omicron": "ο", r"\pi": "π", r"\varpi": "ϖ", r"\rho": "ρ",
    r"\varrho": "ρ", r"\sigma": "σ", r"\varsigma": "ς", r"\tau": "τ",
    r"\upsilon": "υ", r"\phi": "φ", r"\varphi": "φ", r"\chi": "χ",
    r"\psi": "ψ", r"\omega": "ω",
    # 希腊字母大写
    r"\Alpha": "Α", r"\Beta": "Β", r"\Gamma": "Γ", r"\Delta": "Δ",
    r"\Epsilon": "Ε", r"\Zeta": "Ζ", r"\Eta": "Η", r"\Theta": "Θ",
    r"\Iota": "Ι", r"\Kappa": "Κ", r"\Lambda": "Λ", r"\Mu": "Μ",
    r"\Nu": "Ν", r"\Xi": "Ξ", r"\Omicron": "Ο", r"\Pi": "Π",
    r"\Rho": "Ρ", r"\Sigma": "Σ", r"\Tau": "Τ", r"\Upsilon": "Υ",
    r"\Phi": "Φ", r"\Chi": "Χ", r"\Psi": "Ψ", r"\Omega": "Ω",
    # 关系符号
    r"\leq": "≤", r"\ge": "≥", r"\neq": "≠", r"\equiv": "≡",
    r"\approx": "≈", r"\sim": "∼", r"\simeq": "≃", r"\cong": "≅",
    r"\propto": "∝", r"\models": "⊨", r"\perp": "⊥", r"\parallel": "∥",
    r"\mid": "∣", r"\ll": "≪", r"\gg": "≫", r"\prec": "≺",
    r"\succ": "≻", r"\preceq": "⪯", r"\succeq": "⪰", r"\subset": "⊂",
    r"\supset": "⊃", r"\subseteq": "⊆", r"\supseteq": "⊇",
    r"\in": "∈", r"\notin": "∉", r"\ni": "∋", r"\emptyset": "∅",
    r"\varnothing": "∅", r"\implies": "⟹", r"\iff": "⟺",
    # 箭头
    r"\rightarrow": "→", r"\leftarrow": "←", r"\Rightarrow": "⇒",
    r"\Leftarrow": "⇐", r"\leftrightarrow": "↔", r"\Leftrightarrow": "⇔",
    r"\mapsto": "↦", r"\to": "→", r"\gets": "←",
    r"\uparrow": "↑", r"\downarrow": "↓", r"\Uparrow": "⇑",
    r"\Downarrow": "⇓", r"\nearrow": "↗", r"\searrow": "↘",
    r"\nwarrow": "↖", r"\swarrow": "↙",
    r"\Longrightarrow": "⟹", r"\Longleftarrow": "⟸",
    r"\longmapsto": "⟼",
    # 运算符
    r"\times": "×", r"\div": "÷", r"\pm": "±", r"\mp": "∓",
    r"\cdot": "·", r"\ast": "∗", r"\star": "⋆", r"\circ": "∘",
    r"\bullet": "•", r"\oplus": "⊕", r"\ominus": "⊖",
    r"\otimes": "⊗", r"\oslash": "⊘", r"\odot": "⊙",
    r"\sum": "Σ", r"\prod": "Π", r"\coprod": "∐",
    r"\int": "∫", r"\iint": "∬", r"\iiint": "∭",
    r"\oint": "∮", r"\bigcap": "⋂", r"\bigcup": "⋃",
    r"\bigvee": "⋁", r"\bigwedge": "⋀",
    r"\bigoplus": "⨁", r"\bigotimes": "⨂",
    r"\nabla": "∇", r"\partial": "∂",
    r"\forall": "∀", r"\exists": "∃", r"\nexists": "∄",
    r"\lnot": "¬", r"\land": "∧", r"\lor": "∨",
    r"\top": "⊤", r"\bot": "⊥", r"\vdash": "⊢",
    # 集合
    r"\cap": "∩", r"\cup": "∪", r"\setminus": "∖",
    r"\wedge": "∧", r"\vee": "∨", r"\sqcup": "⊔",
    r"\sqcap": "⊓",
    # 其他符号
    r"\infty": "∞", r"\aleph": "ℵ", r"\hbar": "ℏ",
    r"\imath": "ı", r"\jmath": "ȷ", r"\ell": "ℓ",
    r"\wp": "℘", r"\Re": "ℜ", r"\Im": "ℑ",
    r"\angle": "∠", r"\measuredangle": "∡", r"\triangle": "△",
    r"\box": "□", r"\diamond": "◇", r"\clubsuit": "♣",
    r"\diamondsuit": "♦", r"\heartsuit": "♥", r"\spadesuit": "♠",
    r"\star": "⋆", r"\maltese": "✠", r"\checkmark": "✓",
    r"\dag": "†", r"\ddag": "‡", r"\S": "§", r"\P": "¶",
    r"\copyright": "©", r"\pounds": "£",
    r"\dots": "…", r"\cdots": "…", r"\vdots": "⋮", r"\ddots": "⋱",
    # 空格
    r"\,": " ", r"\:": " ", r"\;": " ", r"\quad": "  ",
    r"\qquad": "    ", r"\ ": " ",
}

# 需要保留内容的命令（移除命令，保留花括号内的内容）
_KEEP_CONTENT_RE = re.compile(
    r'\\(text|mathrm|mathbf|textbf|mathit|textit|mathtt|texttt'
    r'|mathbb|mathcal|mathscr|mathfrak|mathsf|rm|bf|it|tt|cal'
    r'|displaystyle|textstyle|scriptstyle'
    r'|thinspace|negthinspace|enspace|hspace|vspace)'
    r'\s*\{([^}]*)\}'
)

# 分数
_FRAC_RE = re.compile(r'\\frac\s*\{([^}]*)\}\s*\{([^}]*)\}')

# 二项式系数
_BINOM_RE = re.compile(r'\\binom\s*\{([^}]*)\}\s*\{([^}]*)\}')

# 开方
_SQRT_RE = re.compile(r'\\sqrt(?:\[([^\]]*)\])?\s*\{([^}]*)\}')

# 上标 (^{...})
_SUPER_RE = re.compile(r'\^\{([^}]*)\}')
# 下标 (_{...})
_SUB_RE = re.compile(r'\_\{([^}]*)\}')

# 上标下标简化（单个字符无花括号）
_SIMPLE_SUPER = re.compile(r'\^([a-zA-Z0-9])')
_SIMPLE_SUB = re.compile(r'_([a-zA-Z0-9])')

# 左/右定界符
_LEFT_RE = re.compile(r'\\left\s*\\?([{}[\]()|.]|\|)')
_RIGHT_RE = re.compile(r'\\right\s*\\?([{}[\]()|.]|\|)')

# 普通LaTeX命令（无参数，由字母组成）
_CMD_RE = re.compile(r'\\([a-zA-Z]+)(?:\s|\b)')


def _replace_keep_content(m: re.Match) -> str:
    """去掉命令前缀，保留花括号内文本"""
    return m.group(2)


def _replace_frac(m: re.Match) -> str:
    a, b = m.group(1).strip(), m.group(2).strip()
    return f"({a})/({b})" if "/" in a or "+" in a or "-" in a else f"{a}/{b}"


def _replace_binom(m: re.Match) -> str:
    return f"C({m.group(1).strip()}, {m.group(2).strip()})"


def _replace_sqrt(m: re.Match) -> str:
    n = m.group(1)
    radicand = m.group(2).strip()
    if n:
        return f"{n}√{radicand}"
    return f"√{radicand}"


def latex_to_unicode(text: str) -> str:
    """
    将 LaTeX 命令替换为可读的 Unicode 文本

    处理顺序（从内到外）：
      1. \\text{...} 等纯文本命令 → 保留内容
      2. \\frac{a}{b} → a/b
      3. \\binom{n}{k} → C(n, k)
      4. \\sqrt[n]{x} → n√x
      5. 上标/下标 → Unicode
      6. \\left, \\right → 删除
      7. 单个命令查表替换
      8. 未知命令 → 删除反斜杠
    """
    # 1. 保留内容的命令
    text = _KEEP_CONTENT_RE.sub(_replace_keep_content, text)

    # 2. 分数
    text = _FRAC_RE.sub(_replace_frac, text)

    # 3. 二项式系数
    text = _BINOM_RE.sub(_replace_binom, text)

    # 4. 开方
    text = _SQRT_RE.sub(_replace_sqrt, text)

    # 5. 上标、下标（花括号形式）
    text = _SUPER_RE.sub(lambda m: f"^{m.group(1)}", text)
    text = _SUB_RE.sub(lambda m: f"_{m.group(1)}", text)

    # 6. 简单上标下标（无花括号）
    text = _SIMPLE_SUPER.sub(lambda m: f"^{m.group(1)}", text)
    text = _SIMPLE_SUB.sub(lambda m: f"_{m.group(1)}", text)

    # 7. 移除 \left \right
    text = _LEFT_RE.sub(lambda m: m.group(1), text)
    text = _RIGHT_RE.sub(lambda m: m.group(1), text)

    # 8. 查表替换（长命令优先）
    for cmd, uni in sorted(_LATEX_TO_UNI.items(), key=lambda x: -len(x[0])):
        text = text.replace(cmd, uni)

    # 9. 剩余未知命令（\command）→ 删除反斜杠
    text = _CMD_RE.sub(lambda m: m.group(1), text)

    return text
