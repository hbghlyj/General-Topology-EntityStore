"""Tests for the backend flow-segmentation layer (ast_to_flow).

The rendering layer (frontend) only lays out the tokens emitted here, so the
semantic decisions — prose vs math, grouping, bolding, script gluing — must be
correct at this level. Run with:

    python3 -m unittest backend.test_flow -v        (from repo root)
    python3 -m unittest test_flow -v                (from backend/)
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

import build_db as bd


def flow(src):
    """Parse a Wolfram box expression and return its flow token lines."""
    ast = bd.Parser(bd.tokenize_wl(src)).parse_expr()
    return bd.ast_to_flow(ast)


def math_values(lines):
    return [t['v'] for line in lines for t in line if t['t'] == 'math']


def text_values(lines):
    return [t['v'] for line in lines for t in line if t['t'] == 'text']


class TestProseMathDistinction(unittest.TestCase):
    def test_prose_runs_are_text_tokens(self):
        lines = flow('RowBox[{"the family ", "F", " of maps ", "X"}]')
        self.assertEqual(text_values(lines), ['the family ', ' of maps '])
        self.assertEqual(math_values(lines), ['F', 'X'])

    def test_connective_with_spaces_is_prose(self):
        # " and" (thin-space separated connective) must be prose, not math
        lines = flow('RowBox[{"A", " and ", "B"}]')
        self.assertIn(' and ', text_values(lines))
        self.assertNotIn('and', math_values(lines))

    def test_single_letters_stay_math(self):
        lines = flow('RowBox[{"F", ",", "d", ",", "n"}]')
        self.assertEqual(math_values(lines), ['F', ',', 'd', ',', 'n'])

    def test_upright_operator_names_are_math_text(self):
        lines = flow('SubscriptBox["Hom", "Top"]')
        self.assertEqual(math_values(lines), ['\\text{Hom}_{\\text{Top}}'])


class TestGrouping(unittest.TestCase):
    def test_paren_template_group_is_atomic(self):
        lines = flow('TemplateBox[{"(", SuperscriptBox["R", "n"], ", ", "d", ")"}, "RowDefault"]')
        self.assertEqual(math_values(lines), ['( R^{n} \\text{, } d )'])

    def test_flat_paren_run_is_atomic(self):
        # parens as flat RowBox children (as in Hom( X , R^n )) stay one chunk
        lines = flow('RowBox[{"Hom", "(", "X", ",", SuperscriptBox["R", "n"], ")"}]')
        vals = math_values(lines)
        self.assertIn('( X , R^{n} )', vals)
        self.assertNotIn('(', vals)
        self.assertNotIn(')', vals)

    def test_nested_parens(self):
        lines = flow('RowBox[{"(", "(", "a", ")", "(", "b", ")", ")"}]')
        self.assertEqual(math_values(lines), ['( ( a ) ( b ) )'])

    def test_set_builder_braces_atomic(self):
        # { f(a) | f ∈ F } with flat brace STR children
        lines = flow('RowBox[{"{", "f", "(", "a", ")", "|", "f", "∈", "F", "}"}]')
        vals = math_values(lines)
        self.assertEqual(len(vals), 1)
        self.assertTrue(vals[0].startswith('{') and vals[0].endswith('}'), vals)

    def test_nested_braces_and_parens(self):
        lines = flow('RowBox[{"{", "(", "x", ")", "(", "y", ")", "}"}]')
        self.assertEqual(math_values(lines), ['{ ( x ) ( y ) }'])

    def test_subsuperscript_structures_are_atomic(self):
        lines = flow('SuperscriptBox[RowBox[{"(", SuperscriptBox["R", "n"], ")"}], "X"]')
        self.assertEqual(math_values(lines), ['( R^{n} )^{X}'])

    def test_dangling_script_glued_to_previous_math(self):
        # source artifact "d -> _{A x A}" with a baseless subscript box
        lines = flow('RowBox[{"d", "→", SubscriptBox["", "A"]}]')
        vals = math_values(lines)
        self.assertTrue(vals[-1].endswith('_{A}'), vals)
        self.assertFalse(any(v[:1] in ('_', '^') for v in vals))


class TestBoldItalicMathVsText(unittest.TestCase):
    def test_bold_identifier_is_mathbf(self):
        lines = flow('StyleBox[x, Bold]')
        self.assertEqual(math_values(lines), ['\\mathbf{x}'])

    def test_bold_general_math_is_boldsymbol(self):
        lines = flow('StyleBox["", Bold, Italic]')  # U+F7B5 = double-struck R
        self.assertEqual(math_values(lines), ['\\boldsymbol{\\mathbb{R}}'])
        self.assertNotIn('\\textbf{\\mathbb{R}}', math_values(lines))

    def test_bold_text_is_textbf(self):
        lines = flow('StyleBox["\\"Top\\"", Bold]')
        self.assertEqual(math_values(lines), ['\\textbf{Top}'])

    def test_italic_text_is_textit(self):
        lines = flow('StyleBox["\\"Topology\\"", Italic]')
        self.assertEqual(math_values(lines), ['\\textit{Topology}'])


class TestStructuralGuarantees(unittest.TestCase):
    def assertWellFormed(self, lines):
        for line in lines:
            for t in line:
                if t['t'] != 'math':
                    continue
                depth = 0
                i = 0
                v = t['v']
                while i < len(v):
                    if v[i] == '\\':
                        i += 2
                        continue
                    if v[i] == '{':
                        depth += 1
                    elif v[i] == '}':
                        depth -= 1
                        self.assertGreaterEqual(depth, 0, v)
                    i += 1
                self.assertEqual(depth, 0, f'unbalanced braces: {v}')
                self.assertNotIn(v[:1], ('_', '^'), f'dangling script: {v}')

    def test_synthetic_well_formed(self):
        self.assertWellFormed(flow('RowBox[{"(", SuperscriptBox["R", "n"], ", ", "d", ")"}, "RowDefault"]'))

    def test_gridbox_rows_become_lines(self):
        lines = flow('GridBox[{{"a"}, {"b"}}]')
        self.assertEqual(len(lines), 2)

    def test_infix_operator_becomes_rel_token(self):
        lines = flow('Infix[{ "A", "B" }, "⊆"]')
        self.assertIn('\\subseteq', math_values(lines))


class TestAscoliIntegration(unittest.TestCase):
    """End-to-end over the real Wolfram EntityStore source."""

    @classmethod
    def setUpClass(cls):
        text = open(bd.WL_PATH, encoding='utf-8').read()
        idx = text.find('"GeneralTopologyTheorem" -> <|')
        idx_ent = text.find('"Entities" -> <|', idx)
        end = bd.find_matching_assoc(text, idx_ent + len('"Entities" -> '))
        entries = bd.get_top_level_entries(text[idx_ent + len('"Entities" -> '):end])
        body = dict(entries)['ClassicalAscolisTheorem']
        props = dict(bd.get_top_level_entries(body))
        rows = bd.parse_summary_grid(props['SummaryGrid'])
        cls.node = [n for h, v, n in rows if h == 'Statement'][0]
        cls.lines = bd.ast_to_flow(cls.node)

    def test_single_wrappable_line(self):
        self.assertEqual(len(self.lines), 1)

    def test_starts_with_prose(self):
        self.assertEqual(self.lines[0][0], {'t': 'text', 'v': 'the family '})

    def test_euclidean_space_group_atomic(self):
        self.assertIn('( \\mathbb{R}^{n} \\text{, } d )', math_values(self.lines))

    def test_hom_subscript_atomic(self):
        self.assertIn('\\text{Hom}_{\\textbf{Top}}', math_values(self.lines))

    def test_bold_reals_is_math_bolding(self):
        vals = ' '.join(math_values(self.lines))
        self.assertIn('\\boldsymbol{\\mathbb{R}}', vals)
        self.assertNotIn('\\textbf{\\mathbb{R}}', vals)
        self.assertNotIn('\\infty', vals)

    def test_well_formed(self):
        for line in self.lines:
            for t in line:
                if t['t'] == 'math':
                    self.assertNotIn(t['v'][:1], ('_', '^'))
                    self.assertEqual(t['v'].count('{'), t['v'].count('}'))

    def test_serializable(self):
        json.dumps(self.lines)


if __name__ == '__main__':
    unittest.main()
