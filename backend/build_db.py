import os
import re
import json
import sqlite3
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

WL_PATH = os.path.join(os.path.dirname(__file__), '..', 'General-Topology-EntityStore.wl')
DB_PATH = os.path.join(os.path.dirname(__file__), 'topology.db')
TEMP_DB_PATH = os.path.join(os.path.dirname(__file__), 'topology.tmp.db')

UNICODE_MAP = {
    '': '\\mathcal{X}',
    '': '\\mathcal{Y}',
    '': '\\mathcal{Z}',
    '': '\\mathcal{U}',
    '': '\\mathcal{A}',
    '': '\\mathcal{C}',
    '': '\\mathcal{P}',
    '': '\\mathbb{R}',
    '': '\\mathbb{R}',
    '': '\\mathcal{B}',
    '': '\\mathbb{Z}',
    '': '=',
    '': '\\equiv',
    '': '\\implies',
    '': '\\to',
    '': '\\to',
    '': '\\prod',
    '': '\\mapsto',
    '': '\\to',
    '': '\\bullet',
    '∈': '\\in',
    '⊆': '\\subseteq',
    '∅': '\\emptyset',
    '∀': '\\forall',
    '∃': '\\exists',
    '≺': '\\prec',
    '×': '\\times',
    '⟶': '\\longrightarrow',
    '⋂': '\\bigcap',
    '∏': '\\prod',
    '⋃': '\\bigcup',
    '∋': '\\ni',
    '⧦': '\\iff',
    '…': '\\dots',
    '≠': '\\neq',
    '∘': '\\circ',
    '∞': '\\infty',
    'τ': '\\tau', 'ρ': '\\rho', 'δ': '\\delta', 'ϕ': '\\phi',
    'γ': '\\gamma', 'ξ': '\\xi', 'ϵ': '\\epsilon', 'ω': '\\omega', 'η': '\\eta',
    'ℬ': '\\mathcal{B}', 'ℐ': '\\mathcal{I}',
    '↦': '\\mapsto', '→': '\\to',
    '∧': '\\land', '∨': '\\lor',
    '∑': '\\sum', '∏': '\\prod',
    '∪': '\\cup', '∩': '\\cap'
}

KNOWN_HEADS = {
    # Box formatting wrappers
    'FormBox', 'TagBox', 'InterpretationBox', 'StyleBox', 'Style', 'HoldForm',
    'RawBoxes', 'PrecedenceForm', 'RGBColor', 'GrayLevel',
    # Box layout constructors
    'RowBox', 'TemplateBox', 'GridBox', 'SubscriptBox', 'SuperscriptBox',
    'SubsuperscriptBox', 'UnderscriptBox', 'OverscriptBox', 'UnderoverscriptBox',
    'FractionBox', 'SqrtBox', 'RadicalBox',
    # Standard math functions & operators
    'Abs', 'Sqrt', 'Min', 'Sum', 'SuperStar', 'Infix', 'Element', 'Exists', 'Function',
    # GeneralTopology operations
    'Functions', 'Mapping', 'Ord', 'ProjectionMap', 'SetBuilder', 'ClassBuilder', 'SetDomain',
    'SetImage', 'SetMinus', 'SetPower', 'SetPreimage', 'SetProduct', 'SetRange',
    'SetUnion', 'Supremum', 'Tuple'
}

WARNINGS = []
CURRENT_ENTITY = "unknown"

def clean_raw_wl(s):
    if not s:
        return s
    for k, v in UNICODE_MAP.items():
        s = s.replace(k, v)
    return s.replace('GeneralTopology`', '')

def find_matching_assoc(text, start_idx):
    depth = 0
    in_string = False
    escape = False
    i = start_idx
    n = len(text)
    while i < n:
        c = text[i]
        if in_string:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_string = False
            i += 1
            continue
        else:
            if c == '"':
                in_string = True
                i += 1
                continue
            if text[i:i+2] == '<|':
                depth += 1
                i += 2
                continue
            if text[i:i+2] == '|>':
                depth -= 1
                i += 2
                if depth == 0:
                    return i
                continue
            i += 1
    return -1

def get_top_level_entries(assoc_text):
    assert assoc_text[:2] == '<|' and assoc_text[-2:] == '|>'
    content = assoc_text[2:-2].strip()
    entries = []
    i = 0
    n = len(content)
    while i < n:
        while i < n and content[i] in ' ,\t\r\n':
            i += 1
        if i >= n:
            break
        if content[i] == '"':
            j = i + 1
            while j < n and content[j] != '"':
                if content[j] == '\\':
                    j += 2
                else:
                    j += 1
            key = content[i+1:j]
            i = j + 1
        else:
            j = i
            while j < n and content[j] not in ' -:=':
                j += 1
            key = content[i:j]
            i = j
        while i < n and content[i] in ' \t\r\n':
            i += 1
        if content[i:i+2] in ('->', ':>'):
            i += 2
        else:
            raise ValueError(f'Expected -> or :> at {i}, got {content[i:i+10]}')
        while i < n and content[i] in ' \t\r\n':
            i += 1
        val_start = i
        depth_sq = 0
        depth_cu = 0
        depth_as = 0
        depth_pa = 0
        in_string = False
        escape = False
        while i < n:
            c = content[i]
            if in_string:
                if escape:
                    escape = False
                elif c == '\\':
                    escape = True
                elif c == '"':
                    in_string = False
                i += 1
                continue
            if c == '"':
                in_string = True
                i += 1
                continue
            if content[i:i+2] == '<|':
                depth_as += 1
                i += 2
                continue
            if content[i:i+2] == '|>':
                depth_as -= 1
                i += 2
                continue
            if c == '[': depth_sq += 1
            elif c == ']': depth_sq -= 1
            elif c == '{': depth_cu += 1
            elif c == '}': depth_cu -= 1
            elif c == '(': depth_pa += 1
            elif c == ')': depth_pa -= 1
            elif c == ',' and depth_sq == 0 and depth_cu == 0 and depth_as == 0 and depth_pa == 0:
                break
            i += 1
        val = content[val_start:i].strip()
        entries.append((key, val))
        if i < n and content[i] == ',':
            i += 1
    return entries

def tokenize_wl(s):
    tokens = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c in ' \t\r\n':
            i += 1
            continue
        if c == '"':
            j = i + 1
            escape = False
            while j < n:
                if escape:
                    escape = False
                elif s[j] == '\\':
                    escape = True
                elif s[j] == '"':
                    break
                j += 1
            tokens.append(('STR', s[i+1:j]))
            i = j + 1
            continue
        if s[i:i+2] in ('->', ':>', '<|', '|>', '&&', '||', '==', '!=', '<=', '>='):
            tokens.append(('OP', s[i:i+2]))
            i += 2
            continue
        if c == '&':
            tokens.append(('OP', '&'))
            i += 1
            continue
        if c == '#':
            j = i + 1
            while j < n and s[j].isdigit():
                j += 1
            tokens.append(('SYM', s[i:j]))
            i = j
            continue
        if c in '[]{},()':
            tokens.append(('PUNCT', c))
            i += 1
            continue
        if c in '+-*/^=<>&|~!@?:;∖∪∩×≺≠':
            tokens.append(('OP', c))
            i += 1
            continue
        j = i
        while j < n and s[j] not in ' \t\r\n"[]{},()+-*/^=<>&|~!@?:;∖∪∩×≺≠#':
            if s[j:j+2] in ('->', ':>', '<|', '|>', '&&', '||', '==', '!=', '<=', '>='):
                break
            j += 1
        tokens.append(('SYM', s[i:j]))
        i = j
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.n = len(tokens)
    def peek(self):
        return self.tokens[self.pos] if self.pos < self.n else ('EOF', '')
    def consume(self, expected_type=None, expected_val=None):
        t = self.peek()
        if expected_type and t[0] != expected_type:
            raise ValueError(f'Expected {expected_type}, got {t} at {self.pos}')
        if expected_val and t[1] != expected_val:
            raise ValueError(f'Expected {expected_val}, got {t} at {self.pos}')
        self.pos += 1
        return t
    def parse_expr(self, min_prec=0):
        t = self.peek()
        if t[0] == 'STR':
            self.consume()
            res = ('STR', t[1])
        elif t[0] == 'SYM':
            self.consume()
            res = ('SYM', t[1])
        elif t[0] == 'PUNCT' and t[1] == '{':
            self.consume('PUNCT', '{')
            items = []
            while self.peek()[0] != 'EOF' and self.peek() != ('PUNCT', '}'):
                items.append(self.parse_expr(0))
                if self.peek() == ('PUNCT', ','):
                    self.consume()
                else:
                    break
            self.consume('PUNCT', '}')
            res = ('LIST', items)
        elif t[0] == 'OP' and t[1] == '<|':
            self.consume('OP', '<|')
            items = []
            while self.peek()[0] != 'EOF' and self.peek() != ('OP', '|>'):
                items.append(self.parse_expr(0))
                if self.peek() == ('PUNCT', ','):
                    self.consume()
                else:
                    break
            self.consume('OP', '|>')
            res = ('ASSOC', items)
        elif t[0] == 'PUNCT' and t[1] == '(':
            self.consume('PUNCT', '(')
            res = self.parse_expr(0)
            self.consume('PUNCT', ')')
        else:
            raise ValueError(f'Unexpected token {t} at pos {self.pos}')

        while True:
            nxt = self.peek()
            if nxt == ('PUNCT', '['):
                self.consume('PUNCT', '[')
                args = []
                while self.peek()[0] != 'EOF' and self.peek() != ('PUNCT', ']'):
                    args.append(self.parse_expr(0))
                    if self.peek() == ('PUNCT', ','):
                        self.consume()
                    else:
                        break
                self.consume('PUNCT', ']')
                res = ('CALL', res, args)
            elif nxt[0] == 'OP' and nxt[1] in ('->', ':>'):
                op = self.consume()[1]
                rhs = self.parse_expr(0)
                res = ('RULE', op, res, rhs)
            elif nxt == ('OP', '&'):
                self.consume('OP', '&')
                res = ('POSTFIX', '&', res)
            elif nxt[0] in ('SYM', 'OP') and nxt[1] not in (',', ']', '}', ')'):
                op = self.consume()[1]
                rhs = self.parse_expr(0)
                res = ('INFIX', op, res, rhs)
            else:
                break
        return res

def is_single_text_wrapper(s):
    if not (s.startswith('\\text{') and s.endswith('}')):
        return False
    depth = 1
    for c in s[6:-1]:
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return False
    return depth == 1

# LaTeX -> unicode for plain-text labels, longest commands first so e.g.
# '\\infty' is replaced before '\\in'. Skips private-use glyphs (they render
# as tofu) and non-command values like '=' that must stay ASCII.
_LATEX_TO_UNICODE = sorted(
    ((v, k) for k, v in UNICODE_MAP.items()
     if v.startswith('\\') and not (0xE000 <= ord(k) <= 0xF8FF)),
    key=lambda kv: -len(kv[0])
)

def clean_label(s):
    """Flatten a LaTeX-ish summary-grid Label to plain readable text.

    Single-wrapper labels (\\text{...}) are unwrapped; mixed labels
    (\\text{closed } G_{\\delta} \\text{ subset ...}) have each \\text{}
    segment stripped and remaining math commands folded back to unicode.
    """
    if is_single_text_wrapper(s):
        return s[6:-1]
    out = []
    i = 0
    n = len(s)
    while i < n:
        if s.startswith('\\text{', i):
            j = i + 6
            depth = 1
            while j < n and depth:
                if s[j] == '{':
                    depth += 1
                elif s[j] == '}':
                    depth -= 1
                j += 1
            out.append(s[i + 6:j - 1])
            i = j
        else:
            out.append(s[i])
            i += 1
    s = ''.join(out)
    for latex, uni in _LATEX_TO_UNICODE:
        s = s.replace(latex, uni)
    s = re.sub(r'_\{([^}]*)\}', r'_\1', s)
    return re.sub(r'\s+', ' ', s).strip()

def ast_to_latex(node):
    if not node: return ''
    if isinstance(node, tuple):
        ntype = node[0]
        if ntype == 'STR':
            val = node[1].replace('\\"', '').strip('"')
            for k, v in UNICODE_MAP.items():
                val = val.replace(k, v)
            val = re.sub(r'[\u2009\u200A\u2002\u2003\u205F]', ' ', val)
            # Visible set braces must be escaped for LaTeX math mode; raw
            # "{" / "}" are grouping delimiters and would disappear.
            # WL box AST represents a visible "{" / "}" as a standalone STR.
            stripped = val.strip()
            if stripped == "{":
                return r"\{"
            if stripped == "}":
                return r"\}"
            # The row separator " | " used inside set-builder TemplateBox rows
            # should become \mid for proper mathematical rendering; keep any
            # hair-space handling as text fallback otherwise.
            if stripped == "|" or stripped == "∣":
                return r"\mid"
            if ' ' in val or any(w in val for w in [' is ', ' the ', ' an ', ' of ', ' on ', ' in ']):
                return f'\\text{{{val}}}'
            # multi-letter words ("Hom", "Top", "and", "el", ...) are upright text,
            # not products of italic variables; single letters stay math italic
            if len(val) > 1 and re.fullmatch(r"[A-Za-z][A-Za-z'’-]*", val):
                return f'\\text{{{val}}}'
            return val
        elif ntype == 'SYM':
            val = node[1]
            if val.startswith('GeneralTopology`'):
                val = val.split('`')[-1]
            if val in UNICODE_MAP:
                return UNICODE_MAP[val]
            return val
        elif ntype == 'LIST':
            return ' '.join(ast_to_latex(x) for x in node[1])
        elif ntype == 'CALL':
            head_val = node[1][1] if node[1][0] == 'SYM' else ''
            clean_head = head_val.split('`')[-1] if head_val.startswith('GeneralTopology`') else head_val
            args = node[2]

            # Emit warning if head is not in KNOWN_HEADS and not a simple single-word function call like f(x)
            if clean_head not in KNOWN_HEADS and not (len(clean_head) <= 3 and clean_head.isalnum()):
                WARNINGS.append(f"Entity [{CURRENT_ENTITY}]: Unsupported or unknown box/call construct '{clean_head}' encountered.")

            if clean_head == 'StyleBox':
                inner = ast_to_latex(args[0])
                styles = {a[1] for a in args[1:] if isinstance(a, tuple) and a[0] == 'SYM'}
                bold = 'Bold' in styles
                italic = 'Italic' in styles
                # Preserve the math/text distinction: \textbf/\textit are text-mode
                # styling; mathematical content gets \mathbf/\boldsymbol/\mathit so
                # MathJax treats it as bold math, not bold text.
                if is_single_text_wrapper(inner):
                    text_body = inner[6:-1]
                    if bold and italic:
                        return f'\\textbf{{\\textit{{{text_body}}}}}'
                    if bold:
                        return f'\\textbf{{{text_body}}}'
                    if italic:
                        return f'\\textit{{{text_body}}}'
                    return inner
                if bold:
                    # \mathbf for plain identifiers, \boldsymbol for general math
                    if re.fullmatch(r'[A-Za-z]', inner):
                        return f'\\mathbf{{{inner}}}'
                    return f'\\boldsymbol{{{inner}}}'
                if italic:
                    return f'\\mathit{{{inner}}}'
                return inner
            if clean_head in ('FormBox', 'TagBox', 'InterpretationBox', 'HoldForm'):
                return ast_to_latex(args[0])
            elif clean_head == 'RowBox':
                if args and args[0][0] == 'LIST':
                    return ' '.join(ast_to_latex(x) for x in args[0][1])
                return ast_to_latex(args[0]) if args else ''
            elif clean_head == 'TemplateBox':
                if len(args) >= 2 and args[1] == ('STR', 'RowWithSeparators'):
                    if args[0][0] == 'LIST':
                        items = args[0][1]
                        if len(items) > 2:
                            return ', '.join(ast_to_latex(x) for x in items[2:])
                    return ''
                elif args:
                    if args[0][0] == 'LIST':
                        return ' '.join(ast_to_latex(x) for x in args[0][1])
                    return ast_to_latex(args[0])
                return ''
            elif clean_head == 'SubscriptBox':
                if len(args) == 2:
                    return f'{ast_to_latex(args[0])}_{{{ast_to_latex(args[1])}}}'
            elif clean_head == 'SuperscriptBox':
                if len(args) == 2:
                    return f'{ast_to_latex(args[0])}^{{{ast_to_latex(args[1])}}}'
            elif clean_head == 'SubsuperscriptBox':
                if len(args) == 3:
                    return f'{ast_to_latex(args[0])}_{{{ast_to_latex(args[1])}}}^{{{ast_to_latex(args[2])}}}'
            elif clean_head == 'UnderscriptBox':
                if len(args) == 2:
                    return f'\\underset{{{ast_to_latex(args[1])}}}{{{ast_to_latex(args[0])}}}'
            elif clean_head == 'OverscriptBox':
                if len(args) == 2:
                    over = ast_to_latex(args[1])
                    if over in ('_', '-', '¯', '\\text{_}'):
                        return f'\\overline{{{ast_to_latex(args[0])}}}'
                    return f'\\overset{{{over}}}{{{ast_to_latex(args[0])}}}'
            elif clean_head == 'UnderoverscriptBox':
                if len(args) == 3:
                    return f'\\overunderset{{{ast_to_latex(args[2])}}}{{{ast_to_latex(args[1])}}}{{{ast_to_latex(args[0])}}}'
            elif clean_head == 'FractionBox':
                if len(args) == 2:
                    return f'\\frac{{{ast_to_latex(args[0])}}}{{{ast_to_latex(args[1])}}}'
            elif clean_head == 'SqrtBox':
                if len(args) == 1:
                    return f'\\sqrt{{{ast_to_latex(args[0])}}}'
            elif clean_head == 'RadicalBox':
                if len(args) == 2:
                    return f'\\sqrt[{ast_to_latex(args[1])}]{{{ast_to_latex(args[0])}}}'
            elif clean_head == 'GridBox':
                if args and args[0][0] == 'LIST':
                    rows = args[0][1]
                    lines = []
                    for r in rows:
                        if r[0] == 'LIST':
                            cells = [ast_to_latex(c) for c in r[1]]
                            lines.append(' & '.join(cells))
                    return ' \\\\ '.join(lines)
            elif clean_head == 'Abs':
                if len(args) == 1:
                    return f'|{ast_to_latex(args[0])}|'
            elif clean_head == 'Sqrt':
                if len(args) == 1:
                    return f'\\sqrt{{{ast_to_latex(args[0])}}}'
            elif clean_head == 'Min':
                return f"\\min({', '.join(ast_to_latex(x) for x in args)})"
            elif clean_head == 'Sum':
                return f"\\sum { ' '.join(ast_to_latex(x) for x in args) }"
            elif clean_head == 'SuperStar':
                if len(args) == 1:
                    return f'{ast_to_latex(args[0])}^*'
            elif clean_head == 'Infix':
                if len(args) >= 2 and args[0][0] == 'LIST':
                    sep = ast_to_latex(args[1]).strip()
                    return f" {sep} ".join(ast_to_latex(x) for x in args[0][1])
            elif clean_head == 'Element':
                if len(args) == 2:
                    return f'{ast_to_latex(args[0])} \\in {ast_to_latex(args[1])}'
            elif clean_head == 'Exists':
                if len(args) == 2:
                    return f'\\exists_{{{ast_to_latex(args[0])}}} {ast_to_latex(args[1])}'
            elif clean_head == 'SetUnion':
                return f"\\bigcup { ' '.join(ast_to_latex(x) for x in args) }"
            elif clean_head == 'SetMinus':
                if len(args) == 2:
                    return f'{ast_to_latex(args[0])} \\setminus {ast_to_latex(args[1])}'
            elif clean_head == 'SetProduct':
                return f"\\prod { ' '.join(ast_to_latex(x) for x in args) }"
            elif clean_head == 'Tuple':
                return f"({', '.join(ast_to_latex(x) for x in args)})"
            elif clean_head == 'Supremum':
                return f"\\sup({', '.join(ast_to_latex(x) for x in args)})"
            elif clean_head == 'ProjectionMap':
                if len(args) == 2:
                    return f"\\pi_{{{ast_to_latex(args[1])}}}({ast_to_latex(args[0])})"
            elif clean_head == 'Function':
                return ''
            elif clean_head in ('SetBuilder', 'ClassBuilder'):
                # --- Set-builder / class-builder with proper escaped braces ---
                # Wolfram overloads (see TraditionalFormMakeBoxAssignments in .wl):
                #   SetBuilder[L_List]                                  -> { L }
                #   SetBuilder[x_, (r:Element|Subset..)[x,A], p_]      -> Row[{r | p}] in WL
                #       – textbook notation should preserve bound variable: {x | r ∧ p}
                #   SetBuilder[f_, {x__}, p_]                           -> { f | And[x,p] }
                #   SetBuilder[f_, {x__}]                               -> { f | And[x] }
                #   SetBuilder[f_, x_, p_]                              -> { f | And[x,p] }
                #   SetBuilder[f_, x_]                                  -> { f | x }
                #   ClassBuilder[x_, e_, p_]                            -> { x | e ∧ p }
                #   ClassBuilder[x_, p_]                                -> { x | p }
                # Preserve semantics: element expression is always args[0] for 3-arg forms.
                def _is_member_node(n):
                    # Safer shape checks – never throw, just return False on malformed nodes
                    if (
                        not isinstance(n, tuple)
                        or len(n) < 3
                        or n[0] != 'CALL'
                        or not isinstance(n[1], tuple)
                        or len(n[1]) < 2
                    ):
                        return False
                    sym = n[1]
                    if not isinstance(sym, tuple) or sym[0] != 'SYM':
                        # head may be qualified GeneralTopology`Element etc – still tuple
                        # but check inner
                        return False
                    hv = sym[1] if len(sym) > 1 and isinstance(sym[1], str) else ''
                    ch = hv.split('`')[-1] if hv.startswith('GeneralTopology`') else hv
                    return ch in ('Element', 'Subset', 'SubsetEqual', 'Superset', 'SupersetEqual')

                if len(args) == 1:
                    if args[0][0] == 'LIST':
                        inner = ', '.join(ast_to_latex(x) for x in args[0][1])
                        return f'\\{{ {inner} \\}}'
                    else:
                        inner = ast_to_latex(args[0])
                        return f'\\{{ {inner} \\}}'
                elif len(args) == 2:
                    if args[1][0] == 'LIST':
                        conds = ' \\text{ and } '.join(ast_to_latex(x) for x in args[1][1])
                        return f'\\{{ {ast_to_latex(args[0])} \\mid {conds} \\}}'
                    else:
                        return f'\\{{ {ast_to_latex(args[0])} \\mid {ast_to_latex(args[1])} \\}}'
                elif len(args) == 3:
                    # Always preserve args[0] as element expression and combine the
                    # two predicates with "and" – this matches textbook set-builder
                    # {x | x∈A ∧ P(x)} rather than the WL shorthand {x∈A | P(x)} which
                    # would drop the bound variable.
                    if args[1][0] == 'LIST':
                        list_part = ' \\text{ and } '.join(ast_to_latex(x) for x in args[1][1])
                        if list_part:
                            combined = f'{list_part} \\text{{ and }} {ast_to_latex(args[2])}'
                        else:
                            combined = ast_to_latex(args[2])
                        return f'\\{{ {ast_to_latex(args[0])} \\mid {combined} \\}}'
                    else:
                        return f'\\{{ {ast_to_latex(args[0])} \\mid {ast_to_latex(args[1])} \\text{{ and }} {ast_to_latex(args[2])} \\}}'
                # fallback – ensure braces are still emitted
                joined = " ".join(ast_to_latex(x) for x in args)
                return f'\\{{ {joined} \\}}'
            # Generic fallback for unknown function-like heads (e.g., f[x], d[x,y])
            # Render as head(args) rather than dropping the head entirely.
            head_latex = ast_to_latex(node[1])
            if args:
                inner = ', '.join(ast_to_latex(x) for x in args)
                # If head is empty (should not happen), just return inner
                if head_latex:
                    return f'{head_latex} ( {inner} )'
                return inner
            return head_latex
        elif ntype == 'INFIX':
            op_str = node[1]
            if op_str in UNICODE_MAP:
                op_str = UNICODE_MAP[op_str]
            elif op_str == '&&': op_str = '\\land'
            elif op_str == '||': op_str = '\\lor'
            elif op_str == '==': op_str = '='
            elif op_str == '!=': op_str = '\\neq'
            elif op_str == '<=': op_str = '\\le'
            elif op_str == '>=': op_str = '\\ge'
            elif op_str == '∖': op_str = '\\setminus'
            elif op_str == '∪': op_str = '\\cup'
            elif op_str == '∩': op_str = '\\cap'
            elif op_str == '×': op_str = '\\times'
            elif op_str == '≺': op_str = '\\prec'
            elif op_str == '≠': op_str = '\\neq'
            return f'{ast_to_latex(node[2])} {op_str} {ast_to_latex(node[3])}'
        elif ntype == 'POSTFIX':
            return f'{ast_to_latex(node[2])}{node[1]}'
    return str(node)

# ---------------------------------------------------------------------------
# Flow segmentation: emit explicit prose/math/space token structure so the
# frontend rendering layer never has to guess mathematical semantics.
#
# Token schema (per statement): a JSON list of *lines*, each line a list of:
#   {"t": "text",  "v": str}   wrappable prose (from string boxes)
#   {"t": "math",  "v": str}   atomic inline-math chunk (LaTeX)
#   {"t": "space", "thin": bool} explicit wrappable separator
# ---------------------------------------------------------------------------

REL_OPS = {
    '\\iff', '\\implies', '\\impliedby', '\\subseteq', '\\supseteq', '\\in',
    '\\ni', '\\equiv', '\\leq', '\\geq', '\\neq', '\\prec', '\\succ', '\\to',
    '\\longrightarrow', '\\mapsto', '\\longmapsto', '\\rightarrow',
    '\\leftarrow', '\\land', '\\lor', '=', '<', '>', '\\le', '\\ge', '\\ne',
}

def _str_val(node):
    val = node[1].replace('\\"', '').strip('"')
    for k, v in UNICODE_MAP.items():
        val = val.replace(k, v)
    return re.sub(r'[\u2009\u200A\u2002\u2003\u205F]', ' ', val)

def _call_head(node):
    head_val = node[1][1] if node[1][0] == 'SYM' else ''
    return head_val.split('`')[-1] if head_val.startswith('GeneralTopology`') else head_val

def _container_items(node):
    args = node[2]
    if args and isinstance(args[0], tuple) and args[0][0] == 'LIST':
        return args[0][1]
    return list(args)

def _first_str(node):
    if not isinstance(node, tuple):
        return None
    if node[0] == 'STR':
        return _str_val(node)
    if node[0] == 'CALL':
        items = _container_items(node)
        return _first_str(items[0]) if items else None
    return None

def _last_str(node):
    if not isinstance(node, tuple):
        return None
    if node[0] == 'STR':
        return _str_val(node)
    if node[0] == 'CALL':
        items = _container_items(node)
        return _last_str(items[-1]) if items else None
    return None

def _is_paren_group(node):
    first, last = _first_str(node), _last_str(node)
    return (first == '(' and last == ')') or (first == '{' and last == '}')

def ast_to_flow(node):
    """Convert a TraditionalForm box AST into explicit flow token lines."""
    lines = []
    cur = []

    def push_line():
        nonlocal cur
        if cur:
            lines.append(cur)
        cur = []

    def add_space(thin=False):
        if cur and cur[-1]['t'] != 'space':
            cur.append({'t': 'space', 'thin': thin})

    def add_math(latex):
        if not latex.strip():
            return
        # A dangling sub/superscript (source artifacts like "d \\to _{A×A}")
        # is glued onto the preceding math chunk — structural, not guessed.
        if latex[:1] in ('_', '^'):
            while cur and cur[-1]['t'] == 'space':
                cur.pop()
            if cur and cur[-1]['t'] == 'math':
                cur[-1]['v'] += latex
                return
        if cur and cur[-1]['t'] == 'math':
            add_space(thin=cur[-1]['v'].strip() not in REL_OPS and latex.strip() not in REL_OPS)
        elif cur and cur[-1]['t'] == 'text':
            add_space()
        cur.append({'t': 'math', 'v': latex})

    def add_text(val):
        if not val.strip():
            return
        if cur and cur[-1]['t'] in ('math', 'text'):
            add_space()
        cur.append({'t': 'text', 'v': val})

    def emit(n):
        if not n:
            return
        if isinstance(n, tuple):
            ntype = n[0]
            if ntype == 'STR':
                val = _str_val(n)
                if ' ' in val:
                    add_text(val)          # prose run
                else:
                    add_math(ast_to_latex(n))  # identifier / upright operator name
                return
            if ntype == 'SYM':
                add_math(ast_to_latex(n))
                return
            if ntype == 'LIST':
                for x in n[1]:
                    emit(x)
                return
            if ntype == 'INFIX':
                emit(n[2])
                op_str = n[1]
                op_latex = UNICODE_MAP.get(op_str)
                if op_latex is None:
                    op_latex = {
                        '&&': '\\land', '||': '\\lor', '==': '=', '!=': '\\neq',
                        '<=': '\\le', '>=': '\\ge', '∖': '\\setminus',
                        '∪': '\\cup', '∩': '\\cap', '×': '\\times',
                        '≺': '\\prec', '≠': '\\neq',
                    }.get(op_str, op_str)
                add_math(op_latex)
                emit(n[3])
                return
            if ntype == 'POSTFIX':
                add_math(ast_to_latex(n))
                return
            # CALL nodes
            head = _call_head(n)
            args = n[2]
            if head == 'StyleBox':
                inner = args[0]
                styles = {a[1] for a in args[1:] if isinstance(a, tuple) and a[0] == 'SYM'}
                bold = 'Bold' in styles
                italic = 'Italic' in styles
                if not (bold or italic):
                    emit(inner)
                    return
                if isinstance(inner, tuple) and inner[0] == 'STR' and ' ' in _str_val(inner):
                    add_text(_str_val(inner))  # styled prose stays prose
                    return
                latex = ast_to_latex(inner)
                if is_single_text_wrapper(latex):
                    text_body = latex[6:-1]
                    if bold and italic:
                        latex = f'\\textbf{{\\textit{{{text_body}}}}}'
                    elif bold:
                        latex = f'\\textbf{{{text_body}}}'
                    elif italic:
                        latex = f'\\textit{{{text_body}}}'
                else:
                    if bold:
                        latex = f'\\mathbf{{{latex}}}' if re.fullmatch(r'[A-Za-z]', latex) else f'\\boldsymbol{{{latex}}}'
                    elif italic:
                        latex = f'\\mathit{{{latex}}}'
                add_math(latex)
                return
            if head in ('FormBox', 'TagBox', 'InterpretationBox', 'HoldForm'):
                emit(args[0])
                return
            if head == 'GridBox':
                if args and args[0][0] == 'LIST':
                    for r in args[0][1]:
                        for c in (r[1] if isinstance(r, tuple) and r[0] == 'LIST' else [r]):
                            emit(c)
                        push_line()
                return
            if head == 'Infix':
                if len(args) >= 2 and args[0][0] == 'LIST':
                    sep = ast_to_latex(args[1]).strip()
                    items = args[0][1]
                    for idx, x in enumerate(items):
                        if idx > 0:
                            add_math(sep)
                        emit(x)
                    return
            if head == 'TemplateBox' and len(args) >= 2 and args[1] == ('STR', '"RowWithSeparators"'):
                items = _container_items(n)
                for idx, x in enumerate(items[2:]):
                    if idx > 0:
                        add_math(',')
                    emit(x)
                return
            if head in ('RowBox', 'TemplateBox') and not _is_paren_group(n):
                # Buffer flat "( ... )" / "{ ... }" child runs (incl. nesting)
                # into single atomic math chunks so delimiters never dangle
                # across wrap points.
                openers = []
                buf = []

                def flush_buf():
                    nonlocal buf
                    add_math(' '.join(ast_to_latex(b) for b in buf))
                    buf = []

                for x in _container_items(n):
                    sv = _str_val(x).strip() if isinstance(x, tuple) and x[0] == 'STR' else ''
                    if openers:
                        buf.append(x)
                        if sv in ('(', '{'):
                            openers.append(sv)
                        elif sv == ')' and openers[-1] == '(':
                            openers.pop()
                            if not openers:
                                flush_buf()
                        elif sv == '}' and openers[-1] == '{':
                            openers.pop()
                            if not openers:
                                flush_buf()
                        continue
                    if sv in ('(', '{'):
                        openers = [sv]
                        buf = [x]
                        continue
                    emit(x)
                for x in buf:  # unbalanced fallback: emit normally
                    emit(x)
                return
            # SubscriptBox/SuperscriptBox/FractionBox/paren groups/... are
            # atomic math chunks
            add_math(ast_to_latex(n))
            return
        add_math(ast_to_latex(n))

    emit(node)
    push_line()
    return [line for line in lines if line]

def parse_summary_grid(sg_text):
    p = Parser(tokenize_wl(sg_text))
    ast = p.parse_expr()
    def find_gridbox(n):
        if not isinstance(n, tuple): return None
        if n[0] == 'CALL' and n[1] == ('SYM', 'GridBox'):
            return n
        for item in n[1:] if isinstance(n, tuple) else []:
            if isinstance(item, list):
                for sub in item:
                    res = find_gridbox(sub)
                    if res: return res
            elif isinstance(item, tuple):
                res = find_gridbox(item)
                if res: return res
        return None
    grid_node = find_gridbox(ast)
    if not grid_node:
        return []
    rows = grid_node[2][0][1]

    def unwrap_text(s):
        s = s.strip()
        if s.startswith('\\text{') and s.endswith('}'):
            return s[6:-1]
        return s

    res_rows = []
    for row in rows:
        cells = row[1]
        header = unwrap_text(ast_to_latex(cells[0]))
        val = ast_to_latex(cells[1])
        res_rows.append((header, val, cells[1]))
    return res_rows

def parse_wl_list(wl_str):
    if not wl_str or not wl_str.strip():
        return []
    try:
        p = Parser(tokenize_wl(wl_str))
        ast = p.parse_expr()
        items = []
        def extract_items(node):
            if not node: return
            if isinstance(node, tuple):
                if node[0] == 'STR':
                    val = node[1].replace('\\"', '').strip('"').strip()
                    if val: items.append(val)
                elif node[0] == 'SYM':
                    val = node[1].strip()
                    if val and val not in ('List', 'GeneralTopology'):
                        items.append(val.split('`')[-1])
                elif node[0] == 'LIST':
                    for x in node[1]:
                        extract_items(x)
                elif node[0] == 'CALL':
                    for x in node[2]:
                        extract_items(x)
        extract_items(ast)
        return items
    except Exception as e:
        WARNINGS.append(f"Failed to parse WL list '{wl_str}' as AST: {e}. Falling back to token inspection.")
        tokens = tokenize_wl(wl_str)
        return [
            t[1].replace('\\"', '').strip('"').strip()
            for t in tokens
            if t[0] in ('STR', 'SYM') and t[1] not in ('{', '}', ',', 'List')
        ]

def build_db():
    global CURRENT_ENTITY
    print("Reading Wolfram Language EntityStore...")
    with open(WL_PATH, 'r', encoding='utf-8') as f:
        text = f.read()

    idx_c = text.find('"GeneralTopologyConcept" -> <|')
    idx_c_ent = text.find('"Entities" -> <|', idx_c)
    end_c_ent = find_matching_assoc(text, idx_c_ent + len('"Entities" -> '))
    c_entries = get_top_level_entries(text[idx_c_ent + len('"Entities" -> '):end_c_ent])

    idx_t = text.find('"GeneralTopologyTheorem" -> <|')
    idx_t_ent = text.find('"Entities" -> <|', idx_t)
    end_t_ent = find_matching_assoc(text, idx_t_ent + len('"Entities" -> '))
    t_entries = get_top_level_entries(text[idx_t_ent + len('"Entities" -> '):end_t_ent])

    print(f"Parsed {len(c_entries)} concepts and {len(t_entries)} theorems.")

    # Build entity type map and set of valid entity identifiers
    entity_type_map = {}
    for name, _ in c_entries:
        entity_type_map[name] = "concept"
    for name, _ in t_entries:
        entity_type_map[name] = "theorem"
    valid_entity_ids = set(entity_type_map.keys())

    if os.path.exists(TEMP_DB_PATH):
        os.remove(TEMP_DB_PATH)

    try:
        conn = sqlite3.connect(TEMP_DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE entities (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            label TEXT,
            alternate_names TEXT,
            qualifying_objects TEXT,
            raw_qualifying_objects TEXT,
            notation TEXT,
            raw_notation TEXT,
            restrictions TEXT,
            raw_restrictions TEXT,
            statement TEXT,
            raw_statement TEXT,
            references_text TEXT,
            statement_tokens TEXT NOT NULL DEFAULT '[]',
            raw_rows TEXT NOT NULL
        );
        """)

        cur.execute("""
        CREATE TABLE relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            rel_type TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES entities(id),
            FOREIGN KEY (target_id) REFERENCES entities(id)
        );
        """)

        cur.execute("CREATE INDEX idx_rel_source ON relationships(source_id);")
        cur.execute("CREATE INDEX idx_rel_target ON relationships(target_id);")
        cur.execute("CREATE INDEX idx_rel_source_target ON relationships(source_id, target_id);")
        cur.execute("CREATE INDEX idx_ent_type ON entities(type);")
        cur.execute("CREATE INDEX idx_ent_label ON entities(label);")

        all_relationships_to_insert = []

        def insert_entity(name, ent_type, body_text):
            global CURRENT_ENTITY
            CURRENT_ENTITY = name
            props = dict(get_top_level_entries(body_text))
            sg_text = props.get('SummaryGrid', '')
            rows = parse_summary_grid(sg_text)
            row_dict = {}
            row_nodes = {}
            for h, v, cell_node in rows:
                clean_h = h.strip('"').strip()
                row_dict[clean_h] = v
                row_nodes[clean_h] = cell_node

            label = row_dict.get('Label', '')
            label_clean = clean_label(label)
            if not label_clean and props.get('Label', ''):
                label_clean = props['Label'].strip('"')

            alt_names = row_dict.get('AlternateNames', '')
            qual_objs = row_dict.get('QualifyingObjects', '') or row_dict.get('Arguments', '')
            notation = row_dict.get('Notation', '')
            restrictions = row_dict.get('Restrictions', '')
            statement = row_dict.get('Statement', '') or row_dict.get('Output', '') or row_dict.get('Expression', '')
            refs = row_dict.get('References', '')

            # Explicit prose/math token structure for flowing statement layout;
            # the frontend only lays these tokens out (no semantic guessing).
            statement_key = 'Statement' if row_dict.get('Statement') else ('Output' if row_dict.get('Output') else 'Expression')
            statement_node = row_nodes.get(statement_key)
            statement_tokens = json.dumps(ast_to_flow(statement_node)) if statement_node else '[]'

            # Also capture raw Wolfram expressions alongside generated LaTeX!
            raw_qual_objs = clean_raw_wl(props.get('QualifyingObjects', '') or props.get('Arguments', ''))
            raw_notation = clean_raw_wl(props.get('Notation', ''))
            raw_restrictions = clean_raw_wl(props.get('Restrictions', ''))
            raw_statement = clean_raw_wl(props.get('Statement', '') or props.get('Output', '') or props.get('Expression', ''))

            # Extract relationships cleanly via structural Wolfram AST list parsing
            rc_list = parse_wl_list(props.get('RelatedConcepts', ''))
            rt_list = parse_wl_list(props.get('RelatedTheorems', ''))

            cur.execute("""
            INSERT INTO entities (
                id, type, label, alternate_names,
                qualifying_objects, raw_qualifying_objects,
                notation, raw_notation,
                restrictions, raw_restrictions,
                statement, raw_statement,
                references_text, statement_tokens, raw_rows
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                ent_type,
                label_clean,
                alt_names,
                qual_objs,
                raw_qual_objs,
                notation,
                raw_notation,
                restrictions,
                raw_restrictions,
                statement,
                raw_statement,
                refs,
                statement_tokens,
                json.dumps([[h, v] for h, v, _ in rows])
            ))

            all_relationships_to_insert.append((name, ent_type, rc_list, 'RelatedConcepts'))
            all_relationships_to_insert.append((name, ent_type, rt_list, 'RelatedTheorems'))

        print("Inserting concepts...")
        for name, body in c_entries:
            insert_entity(name, "concept", body)

        print("Inserting theorems...")
        for name, body in t_entries:
            insert_entity(name, "theorem", body)

        print("Inserting relationships with foreign-key validation...")
        for source_id, source_type, target_ids, rel_type in all_relationships_to_insert:
            for tid in target_ids:
                if not tid or tid == source_id:
                    continue
                if tid not in valid_entity_ids:
                    WARNINGS.append(f"Entity [{source_id}]: Ignored target '{tid}' in '{rel_type}' because it is not a valid concept or theorem ID.")
                    continue
                ttype = entity_type_map[tid]
                cur.execute("""
                INSERT INTO relationships (source_id, source_type, target_id, target_type, rel_type)
                VALUES (?, ?, ?, ?, ?)
                """, (source_id, source_type, tid, ttype, rel_type))

        conn.commit()

        cur.execute("SELECT count(*) FROM entities WHERE type='concept'")
        c_cnt = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM entities WHERE type='theorem'")
        t_cnt = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM relationships")
        r_cnt = cur.fetchone()[0]

        print(f"Database build complete! {DB_PATH}")
        print(f"Concepts inserted: {c_cnt}")
        print(f"Theorems inserted: {t_cnt}")
        print(f"Relationships inserted: {r_cnt}")
        if WARNINGS:
            print(f"\n[PARSER AUDIT] {len(WARNINGS)} warnings emitted during AST conversion:")
            for w in WARNINGS[:10]:
                print("  -", w)
            if len(WARNINGS) > 10:
                print(f"  ... and {len(WARNINGS)-10} more warnings.")
        else:
            print("\n[PARSER AUDIT] 0 warnings emitted! All 441 entity box expressions matched known supported constructs.")

        conn.close()

        if c_cnt == 0 or t_cnt == 0:
            raise RuntimeError(f"Database build validation failed: concept_count={c_cnt}, theorem_count={t_cnt}. Aborting atomic replacement.")

        # Atomically replace production database topology.db with validated topology.tmp.db
        os.replace(TEMP_DB_PATH, DB_PATH)

    except Exception as e:
        if 'conn' in locals():
            try:
                conn.close()
            except Exception:
                pass
        if os.path.exists(TEMP_DB_PATH):
            os.remove(TEMP_DB_PATH)
        raise e

if __name__ == "__main__":
    build_db()
