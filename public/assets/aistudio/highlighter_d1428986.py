# -*- coding: utf-8 -*-
"""Подсветка синтаксиса G-кода."""

import re
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


class GCodeHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.rules = []

        def add(p, c, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(c))
            if bold:
                f.setFontWeight(QFont.Bold)
            if italic:
                f.setFontItalic(True)
            self.rules.append((re.compile(p), f))
        add(r"\([^)]*\)", "#6a9955", italic=True)
        add(r"%.*", "#888888", italic=True)
        add(r"\bN\d+\b", "#dcdcaa")
        add(r"\bG0?[0-9]{1,3}(\.[0-9]+)?\b", "#569cd6", bold=True)
        add(r"\bM[0-9]+\b", "#c586c0", bold=True)
        add(r"\b[XYZIJKRFSPQDHL]-?\d+(\.\d+)?\b", "#9cdcfe")
        add(r"\bT\d+\b", "#4ec9b0")
        add(r"\bIF\b|\bGOTO\b|\bEQ\b|\bNE\b|\bGT\b|\bLT\b|\bGE\b|\bLE\b",
            "#ce9178", bold=True)
        add(r"#\d+", "#f44747")

    def highlightBlock(self, text):
        for pat, fmt in self.rules:
            for m in pat.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)
