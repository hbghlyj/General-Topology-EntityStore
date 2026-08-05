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
        # { f(a) | f ∈ F } with flat brace STR children – visible braces must be escaped
        lines = flow('RowBox[{"{", "f", "(", "a", ")", "|", "f", "∈", "F", "}"}]')
        vals = math_values(lines)
        self.assertEqual(len(vals), 1)
        # LaTeX visible braces are \{ \} so the chunk should start with \{ and end with \}
        self.assertTrue(vals[0].startswith(r'\{') and vals[0].endswith(r'\}'), vals)
        # pipe should be rendered as \mid (not raw \"|\" text) for proper math
        self.assertIn(r'\mid', vals[0])

    def test_nested_braces_and_parens(self):
        lines = flow('RowBox[{"{", "(", "x", ")", "(", "y", ")", "}"}]')
        self.assertEqual(math_values(lines), [r'\{ ( x ) ( y ) \}'])

    def test_subsuperscript_structures_are_atomic(self):
        lines = flow('SuperscriptBox[RowBox[{"(", SuperscriptBox["R", "n"], ")"}], "X"]')
        self.assertEqual(math_values(lines), ['( R^{n} )^{X}'])

    def test_dangling_script_glued_to_previous_math(self):
        # source artifact "d -> _{A x A}" with a baseless subscript box
        lines = flow('RowBox[{"d", "→", SubscriptBox["", "A"]}]')
        vals = math_values(lines)
        self.assertTrue(vals[-1].endswith('_{A}'), vals)
        self.assertFalse(any(v[:1] in ('_', '^') for v in vals))

    def test_set_builder_three_arg_element_preserves_bound_variable(self):
        # Regression: 3-arg Element case must NOT drop the bound variable.
        # Wolfram WL: SetBuilder[x, Element[x,A], P(x)] should be {x | x∈A and P}
        # not {x∈A | P}.  This preserves mathematical meaning.
        latex = bd.ast_to_latex(
            bd.Parser(bd.tokenize_wl('SetBuilder[x, Element[x, A], P[x]]')).parse_expr()
        )
        self.assertTrue(latex.startswith(r'\{'), latex)
        self.assertTrue(latex.endswith(r'\}'), latex)
        self.assertIn(r'\mid', latex)
        # bound variable x must still appear as element expression
        self.assertIn('x', latex)
        # membership and predicate both present and combined with "and"
        self.assertIn(r'\in', latex)
        self.assertIn('and', latex)
        # Should be of form {x | x∈A and P} – element before \mid, not dropped
        before_mid, after_mid = latex.split(r'\mid')
        self.assertIn('x', before_mid)
        self.assertIn(r'\in', after_mid)

    def test_set_builder_direct_call(self):
        # 2-arg case used in Ascoli notation
        latex = bd.ast_to_latex(
            bd.Parser(bd.tokenize_wl('SetBuilder[f[a], Element[f, F]]')).parse_expr()
        )
        self.assertEqual(latex, r'\{ f ( a ) \mid f \in F \}')

    def test_class_builder_two_and_three_args(self):
        # ClassBuilder[x, p] -> {x | p}
        latex2 = bd.ast_to_latex(
            bd.Parser(bd.tokenize_wl('ClassBuilder[x, P[x]]')).parse_expr()
        )
        self.assertEqual(latex2, r'\{ x \mid P ( x ) \}')
        # ClassBuilder[x, e, p] -> {x | e and p}
        latex3 = bd.ast_to_latex(
            bd.Parser(bd.tokenize_wl('ClassBuilder[x, Element[x, A], Q[x]]')).parse_expr()
        )
        self.assertTrue(latex3.startswith(r'\{ x \mid'), latex3)
        self.assertIn(r'\in', latex3)
        self.assertIn('and', latex3)

    def test_unknown_head_fallback_preserves_information(self):
        # Generic CALL fallback should render as head(args) not silently drop head
        latex = bd.ast_to_latex(
            bd.Parser(bd.tokenize_wl('MyFunc[a, b]')).parse_expr()
        )
        # Should contain head and both args
        self.assertIn('MyFunc', latex)
        self.assertIn('a', latex)
        self.assertIn('b', latex)
        # Should be parenthesized form, not just "a b"
        self.assertNotEqual(latex.strip(), 'a b')

    def test_is_member_node_robustness_malformed(self):
        # _is_member_node equivalent logic should not throw on malformed nodes.
        # We test ast_to_latex with 3-arg SetBuilder where second arg is not a CALL
        # but a plain SYM, ensuring fallback path works without exception.
        try:
            latex = bd.ast_to_latex(
                bd.Parser(bd.tokenize_wl('SetBuilder[x, y, z]')).parse_expr()
            )
        except Exception as e:
            self.fail(f'ast_to_latex raised on malformed second arg: {e}')
        self.assertTrue(latex.startswith(r'\{'), latex)
        self.assertIn(r'\mid', latex)


class TestBoldItalicMathVsText(unittest.TestCase):
    def test_is_single_text_wrapper_helper(self):
        self.assertTrue(bd.is_single_text_wrapper(r"\text{A{B}}"))
        self.assertFalse(bd.is_single_text_wrapper(r"\text{A}\text{B}"))

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

    def test_bold_rowbox_text_is_textbf(self):
        lines = flow('StyleBox[RowBox[{"Topology"}], Bold]')
        self.assertEqual(math_values(lines), ['\\textbf{Topology}'])

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


class TestCleanLabel(unittest.TestCase):
    def test_single_text_wrapper_unwrapped(self):
        self.assertEqual(bd.clean_label('\\text{Urysohn Lemma}'), 'Urysohn Lemma')

    def test_plain_label_unchanged(self):
        self.assertEqual(bd.clean_label('Compactness'), 'Compactness')

    def test_mixed_text_and_math_flattened(self):
        # regression: naive \\text{...} stripping corrupted mixed labels into
        # 'closed } G_{\delta} \text{ subset of ...'
        s = '\\text{closed } G_{\\delta} \\text{ subset of normal space}'
        self.assertEqual(bd.clean_label(s), 'closed G_δ subset of normal space')

    def test_trailing_math_segment(self):
        s = '\\text{is } G_{\\delta} \\text{ in}'
        self.assertEqual(bd.clean_label(s), 'is G_δ in')

    def test_leading_text_segment_only(self):
        s = '\\text{closed subset of regular space with countably locally finite basis is } G_{\\delta}'
        self.assertEqual(bd.clean_label(s), 'closed subset of regular space with countably locally finite basis is G_δ')


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
