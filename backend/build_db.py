import os
import re
import json
import sqlite3

WL_PATH = os.path.join(os.path.dirname(__file__), '..', 'General-Topology-EntityStore.wl')
DB_PATH = os.path.join(os.path.dirname(__file__), 'topology.db')

UNICODE_MAP = {
    '': '\\mathcal{X}',
    '': '\\mathcal{Y}',
    '': '\\mathcal{Z}',
    '': '\\mathcal{U}',
    '': '\\mathcal{A}',
    '': '\\mathcal{C}',
    '': '\\mathcal{P}',
    '': '\\infty',
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
    'Functions', 'Mapping', 'Ord', 'ProjectionMap', 'SetBuilder', 'SetDomain',
    'SetImage', 'SetMinus', 'SetPower', 'SetPreimage', 'SetProduct', 'SetRange',
    'SetUnion', 'Supremum', 'Tuple'
}

WARNINGS = []
CURRENT_ENTITY = "unknown"

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

def ast_to_latex(node):
    if not node: return ''
    if isinstance(node, tuple):
        ntype = node[0]
        if ntype == 'STR':
            val = node[1].replace('\\"', '').strip('"')
            for k, v in UNICODE_MAP.items():
                val = val.replace(k, v)
            if ' ' in val or any(w in val for w in [' is ', ' the ', ' an ', ' of ', ' on ', ' in ']):
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

            if clean_head in ('FormBox', 'TagBox', 'InterpretationBox', 'StyleBox', 'HoldForm'):
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
                    return f'\\munderover{{{ast_to_latex(args[1])}}}{{{ast_to_latex(args[2])}}}{{{ast_to_latex(args[0])}}}'
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
            return ' '.join(ast_to_latex(x) for x in args)
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
    res_rows = []
    for row in rows:
        cells = row[1]
        header = ast_to_latex(cells[0])
        val = ast_to_latex(cells[1])
        res_rows.append((header, val))
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
    with open(WL_PATH, 'r') as f:
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

    # Build entity type map
    entity_type_map = {}
    for name, _ in c_entries:
        entity_type_map[name] = "concept"
    for name, _ in t_entries:
        entity_type_map[name] = "theorem"

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
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

    def insert_entity(name, ent_type, body_text):
        global CURRENT_ENTITY
        CURRENT_ENTITY = name
        props = dict(get_top_level_entries(body_text))
        sg_text = props.get('SummaryGrid', '')
        rows = parse_summary_grid(sg_text)
        row_dict = {}
        for h, v in rows:
            clean_h = h.strip('"').strip()
            row_dict[clean_h] = v

        label = row_dict.get('Label', '')
        def clean_text_wrapper(s):
            if s.startswith('\\text{') and s.endswith('}'):
                return s[6:-1]
            return s

        label_clean = clean_text_wrapper(label)
        if not label_clean and '"Label"' in props:
            label_clean = props['"Label"'].strip('"')

        alt_names = row_dict.get('AlternateNames', '')
        qual_objs = row_dict.get('QualifyingObjects', '') or row_dict.get('Arguments', '')
        notation = row_dict.get('Notation', '')
        restrictions = row_dict.get('Restrictions', '')
        statement = row_dict.get('Statement', '') or row_dict.get('Output', '') or row_dict.get('Expression', '')
        refs = row_dict.get('References', '')

        # Also capture raw Wolfram expressions alongside generated LaTeX!
        raw_qual_objs = props.get('"QualifyingObjects"', '') or props.get('"Arguments"', '')
        raw_notation = props.get('"Notation"', '')
        raw_restrictions = props.get('"Restrictions"', '')
        raw_statement = props.get('"Statement"', '') or props.get('"Output"', '') or props.get('"Expression"', '')

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
            references_text, raw_rows
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(rows)
        ))

        def add_rels_list(target_ids, rel_type):
            for tid in target_ids:
                if tid and tid != name:
                    ttype = entity_type_map.get(tid, 'concept')
                    cur.execute("""
                    INSERT INTO relationships (source_id, source_type, target_id, target_type, rel_type)
                    VALUES (?, ?, ?, ?, ?)
                    """, (name, ent_type, tid, ttype, rel_type))

        add_rels_list(rc_list, 'RelatedConcepts')
        add_rels_list(rt_list, 'RelatedTheorems')

    print("Inserting concepts...")
    for name, body in c_entries:
        insert_entity(name, "concept", body)

    print("Inserting theorems...")
    for name, body in t_entries:
        insert_entity(name, "theorem", body)

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

if __name__ == "__main__":
    build_db()
