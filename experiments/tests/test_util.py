#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Tests for util.py.

from importlib import reload
import pytest


@pytest.fixture
def util():
    import util as mod
    reload(mod)
    return mod


# ----------------- replace_html_anomalies_and_special_chars -------------------

def test_replace_html_anomalies_and_special_chars(util):
    s = "Hello âĢĶ âĢĵ âĢľ âĢĿ âĢĺ âĢĻ âĢĭ âĢ¦ Ġ Ċ <0x0A> ĉ ▁."
    expected = """Hello — – " " ' '   ...   \n \n \t  ."""
    output = util.replace_html_anomalies_and_special_chars(s)
    print(f"Output: {output}")
    print(f"Expected: {expected}")
    assert output == expected

def test_batch_replace_html_anomalies_and_special_chars(util):
    tokens = ['âĢĶ', 'âĢ', 'ĵ' ]
    activations = [0.1, 0.2, 0.3]
    expected_tokens = ['—', '–']
    expected_activations = [0.1, 0.3]
    out_tokens, out_activations = util.batch_replace_html_anomalies_and_special_chars(tokens, activations)
    assert out_tokens == expected_tokens
    assert out_activations == expected_activations


# ------------------------------- format_data_string ---------------------------

def test_format_data_string_keeps_breaks(util):
    tokens = ["Hello", "\n", "world", "!"]
    out = util.format_data_string(tokens, show_breaks=True)
    assert out == "Hello\nworld!"


def test_format_data_string_strips_breaks(util):
    tokens = ["a", "\n", "b", "\n", "c"]
    out = util.format_data_string(tokens, show_breaks=False)
    assert out == "a b c"  # newlines replaced by single spaces


# ----------------------------- format_activation_string ----------------------

def test_format_activation_string_basic_markers_when_not_showing_values(util):
    tokens = ["a", "b", "c"]
    acts = [0.0, 0.2, -0.1]
    # show_activations=False; positive activations bracketed
    out = util.format_activation_string(tokens, acts,
                                        show_activations=False,
                                        show_null_activations=False,
                                        merge_activations=False,
                                        show_breaks=True,
                                        activation_threshold=0)
    assert out == "a<<b>>c"


def test_format_activation_string_merge_removes_adjacent_markers(util):
    tokens = ["a", "b", "c"]
    acts = [0.1, 0.2, 0.0]  # first two positive → contiguous markers
    out = util.format_activation_string(tokens, acts,
                                        show_activations=False,
                                        show_null_activations=False,
                                        merge_activations=True,
                                        show_breaks=True,
                                        activation_threshold=0)
    # Without merge, we'd get "<<a>><<b>>c"; with merge, the ">><<" is removed → "<<ab>>c"
    assert out == "<<ab>>c"

def test_format_activation_string_threshold(util):
    tokens = ["a", "b", "c"]
    acts = [0.1, 0.2, 0.0]  # first two positive → contiguous markers
    out = util.format_activation_string(tokens, acts,
                                        show_activations=False,
                                        show_null_activations=False,
                                        merge_activations=True,
                                        show_breaks=True,
                                        activation_threshold=0.15)
    # Without merge, we'd get "<<a>><<b>>c"; with merge, the ">><<" is removed → "<<ab>>c"
    assert out == "a<<b>>c"

def test_format_activation_string_show_values_only_for_positive(util):
    tokens = ["A", "B", "C"]
    acts = [0.0, 0.05, -0.02]
    out = util.format_activation_string(tokens, acts,
                                        show_activations=True,
                                        show_null_activations=False,
                                        merge_activations=False,
                                        show_breaks=True,
                                        activation_threshold=0)
    # only the positive gets annotated, with one decimal
    assert out == "A" "B<<0.1>>" "C"


def test_format_activation_string_show_values_including_nulls(util):
    tokens = ["x", "y"]
    acts = [0.0, 1.234]
    out = util.format_activation_string(tokens, acts,
                                        show_activations=True,
                                        show_null_activations=True,
                                        merge_activations=False,
                                        show_breaks=True,
                                        activation_threshold=0)
    # both get annotated; values rounded to one decimal
    assert out == "x<<0.0>>y<<1.2>>"


def test_format_activation_string_strips_breaks(util):
    tokens = ["foo", "\n", "bar"]
    acts = [0.3, 0.0, 0.4]
    out = util.format_activation_string(tokens, acts,
                                        show_activations=False,
                                        show_null_activations=False,
                                        merge_activations=False,
                                        show_breaks=False,
                                        activation_threshold=0)
    assert out == "<<foo>>  <<bar>>".replace("  ", " ")  # newline becomes space


def test_format_activation_string_mismatch_lengths_assert(util):
    tokens = ["a", "b"]
    acts = [0.1]
    with pytest.raises(AssertionError) as ei:
        util.format_activation_string(tokens, acts,
                                      show_activations=False,
                                      show_null_activations=False,
                                      merge_activations=False,
                                      show_breaks=True,
                                      activation_threshold=0)
    assert "same length" in str(ei.value)


def test_format_activation_string_invalid_combination_nulls_without_values(util):
    with pytest.raises(AssertionError) as ei:
        util.format_activation_string(["a"], [0.0],
                                      show_activations=False,
                                      show_null_activations=True,   # invalid with show_activations=False
                                      merge_activations=False,
                                      show_breaks=True,
                                      activation_threshold=0)
    assert "Cannot show null activations when not showing activations" in str(ei.value)


def test_format_activation_string_invalid_combination_merge_with_values(util):
    with pytest.raises(AssertionError) as ei:
        util.format_activation_string(["a"], [0.5],
                                      show_activations=True,        # invalid with merge
                                      show_null_activations=False,
                                      merge_activations=True,
                                      show_breaks=True,
                                      activation_threshold=0)
    assert "Cannot merge activations when showing activations" in str(ei.value)


# ------------------------------- snip_activations -----------------------------

def test_snip_activations_center_window(util):
    tokens = list("abcdefghij")
    acts = [0, 0, 0.1, 0, 2.0, 0, 0.2, 0, 0, 0]  # max at index 4
    out_t, out_a = util.snip_activations(tokens, acts, length_in_tokens=5)
    # indices 2..6 inclusive (2 before & after around index 4)
    assert out_t == list("cdefg")
    assert out_a == acts[2:7]


def test_snip_activations_respects_start_bound(util):
    tokens = list("abcde")
    acts = [10, 1, 2, 3, 4]  # max at index 0
    out_t, out_a = util.snip_activations(tokens, acts, length_in_tokens=5)
    assert out_t == list("abc")  # start bound at 0; up to index 3
    assert out_a == acts[0:3]


def test_snip_activations_handle_positive_length(util):
    tokens = list("abcdefg")
    acts = [0, 1, 2, 3, 10, 5, 6]
    out_t, out_a = util.snip_activations(tokens, acts, length_in_tokens=4)
    assert out_t == list("cdef")
    assert out_a == acts[2:6]


def test_snip_activations_respects_end_bound(util):
    tokens = list("abcde")
    acts = [1, 2, 3, 4, 10] # max at last index
    out_t, out_a = util.snip_activations(tokens, acts, length_in_tokens=5)
    assert out_t == list("cde") # from index 2 to end
    assert out_a == acts[2:5]


def test_snip_activations_handle_no_max(util):
    tokens = list("abcde")
    acts = [0, 0, 0, 0, 0]  # max nowhere
    out_t, out_a = util.snip_activations(tokens, acts, length_in_tokens=3)
    assert out_t == list("bcd")
    assert out_a == acts[2:5]


def test_snip_activations_length_mismatch(util):
    with pytest.raises(AssertionError):
        util.snip_activations(["a", "b"], [0.1], length_in_tokens=3)


# ------------------------------ batch_snip_activations ------------------------

def test_batch_snip_activations_multiple_examples(util):
    tokens = [list("abcde"), list("wxyz")]
    acts = [
        [0, 1, 10, 2, 0],   # max at index 2; include 1 before/after
        [0, 5, 1, 0],       # max at index 1; include 1 before/after
    ]
    out_t, out_a = util.batch_snip_activations(tokens, acts, length_in_tokens=3)
    assert out_t == [list("bcd"), list("wxy")]
    assert out_a == [[1, 10, 2], [0, 5, 1]]


def test_batch_snip_activations_mismatch_examples(util):
    with pytest.raises(AssertionError):
        util.batch_snip_activations([["a"]], [], length_in_tokens=3)


# ------------------------------ remove_duplicate_snippets ---------------------

def test_remove_duplicate_snippets_preserves_first_occurrence_and_order(util):
    tokens = [
        list("hello"),       # "hello" (keep)
        ["he", "llo"],       # joins to "hello" (drop)
        list("world"),       # "world" (keep)
        list("hello"),       # "hello" again (drop)
        ["wor", "ld"],       # "world" again (drop)
        list("unique"),      # "unique" (keep)
    ]
    acts = [
        [1, 2, 3, 4, 5],
        [9, 9, 9, 9, 9],
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [7, 7, 7, 7, 7],
        [8, 8, 8, 8, 8],
        [0.9],
    ]
    out_t, out_a = util.remove_duplicate_snippets(tokens, acts)
    assert out_t == [list("hello"), list("world"), list("unique")]
    assert out_a == [
        [1, 2, 3, 4, 5],
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [0.9],
    ]


def test_remove_duplicate_snippets_mismatch(util):
    with pytest.raises(AssertionError):
        util.remove_duplicate_snippets([["a"]], [])


# ----------------------------------- is_number --------------------------------

@pytest.mark.parametrize(
    "s,expected",
    [
        ("0", True),
        ("3.14", True),
        ("-2.5", True),
        ("1e-3", True),
        ("+.5", True),
        ("NaN", True),   # float("nan") works, even if not finite
        ("inf", True),
        ("-INF", True),
        ("", False),
        (" ", False),
        ("3,14", False),
        ("abc", False),
        ("12a", False),
    ],
)
def test_is_number(util, s, expected):
    assert util.is_number(s) is expected
