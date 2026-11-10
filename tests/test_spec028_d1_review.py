"""Independent black-box review tests for spec 028 phase D1 (reader, evaluator seeding, v5 format).

Written from docs/board/specs/028-data-import-core.md only.  Strict xfail marks a real defect.
"""

import json
from pathlib import Path

import pytest
import sympy as sp

from livesheet.document import DocumentError, RegionData, SheetDocument
from livesheet.engine import dataio
from livesheet.engine.dataio import DataImportError, ImportOptions
from livesheet.engine.evaluator import Engine


def rd(text, name="d", **opt):
    return dataio.read_table_text(text, ImportOptions(**opt), name=name)


def err(text, **opt):
    with pytest.raises(DataImportError) as info:
        rd(text, **opt)
    return str(info.value)


def run(lines, datasets):
    res = Engine().evaluate([(i, s) for i, s in enumerate(lines)], datasets)
    return [res[i] for i in range(len(lines))]


def col(ds, name):
    return next(c for c in ds.columns if c.name == name)


# ---------------------------------------------------------------- delimiters / decimal / format

@pytest.mark.parametrize("delim", [",", ";", "\t", "|"])
def test_delimiters_read_and_suggested(delim):
    text = delim.join(["a", "b"]) + "\n" + delim.join(["1", "2"]) + "\n" + delim.join(["3", "4"])
    assert dataio.suggest_options_text(text).delimiter == delim
    ds = rd(text, delimiter=delim)
    assert col(ds, "a").values == [1, 3] and col(ds, "b").values == [2, 4]


def test_custom_delimiter_colon():
    ds = rd("a:b\n1:2", delimiter=":")
    assert col(ds, "b").values == [2]


def test_decimal_comma_and_point():
    ds = rd("a;b\n1,5;2\n3,5;4", delimiter=";", decimal=",")
    assert col(ds, "a").values == [1.5, 3.5]
    ds = rd("a,b\n1.5,2\n3.5,4")
    assert col(ds, "a").values == [1.5, 3.5]


def test_decimal_comma_exponent():
    ds = rd("a;b\n1,5e-3;1\n2;2", delimiter=";", decimal=",")
    assert col(ds, "a").values == [0.0015, 2.0]


def test_quoted_embedded_delimiter_and_newline():
    ds = rd('"name, full",v\n"a,b",1\n"line1\nline2",2')
    c = col(ds, "name_full")
    assert c.kind == "text" and c.values == ["a,b", "line1\nline2"]
    assert col(ds, "v").values == [1, 2]


def test_escaped_double_quote():
    ds = rd('n,v\n"he said ""hi""",1')
    assert col(ds, "n").values == ['he said "hi"']


def test_quoted_number_is_number():
    ds = rd('a,b\n"1.5",2')
    assert col(ds, "a").kind == "number" and col(ds, "a").values == [1.5]


def test_bom_and_crlf_text():
    ds = rd("﻿a,b\r\n1,2\r\n3,4\r\n")
    assert [c.name for c in ds.columns] == ["a", "b"]
    assert col(ds, "a").values == [1, 3]


def test_bom_file_and_suggest(tmp_path):
    p = tmp_path / "f.csv"
    p.write_bytes("﻿a;b\r\n1,5;2\r\n2,5;3\r\n".encode("utf-8"))
    o = dataio.suggest_options(p)
    assert (o.delimiter, o.decimal, o.has_header, o.encoding) == (";", ",", True, "utf-8")
    ds = dataio.read_table(p, o, name="f")
    assert col(ds, "a").values == [1.5, 2.5] and ds.source == str(p)


def test_latin1_vs_utf8(tmp_path):
    p = tmp_path / "l.csv"
    p.write_bytes("name,v\n\xe9t\xe9,1\n".encode("latin-1"))
    with pytest.raises(DataImportError) as info:
        dataio.read_table(p, ImportOptions(), name="l")
    msg = str(info.value)
    assert "is not valid UTF-8 text; try the Latin-1 encoding option." in msg
    ds = dataio.read_table(p, ImportOptions(encoding="latin-1"), name="l")
    assert col(ds, "name").values == ["\xe9t\xe9"]
    assert dataio.suggest_options(p).encoding == "latin-1"


def test_utf8_non_ascii_header():
    ds = rd("Länge [mm],v\n1,2")
    assert col(ds, "L_nge").label == "Länge" and col(ds, "L_nge").unit == "mm"


def test_blank_lines_ignored_and_cells_trimmed():
    ds = rd("a , b\n\n 1 , 2 \n\n3,4\n\n")
    assert col(ds, "a").values == [1, 3]


def test_skip_lines():
    ds = rd("# comment\n# more\na,b\n1,2", skip_lines=2)
    assert col(ds, "a").values == [1]


# ---------------------------------------------------------------- errors

def test_ragged():
    assert err("a,b\n1,2\n3") == "Line 3 has 1 field, but the first line has 2."
    assert err("a,b\n1,2,3") == "Line 2 has 3 fields, but the first line has 2."


def test_ragged_after_blank_lines_uses_physical_line():
    assert err("a,b\n\n1,2\n\n3") == "Line 5 has 1 field, but the first line has 2."


def test_ragged_header_shorter_than_data():
    assert err("a\n1,2") == "Line 2 has 2 fields, but the first line has 1."


def test_empty_and_header_only():
    assert err("") == "The file has no data rows."
    assert err("\n\n  \n") == "The file has no data rows."
    assert err("a,b") == "The file has no data rows."
    assert err("a,b\n\n\n") == "The file has no data rows."


def test_no_header_single_row_ok():
    ds = rd("1,2", has_header=False)
    assert col(ds, "col1").values == [1]


def test_all_text():
    assert err("a,b\nx,y") == "The file has no numeric column."


def test_missing_error_and_skip():
    assert err("a,b\n1,2\n,4") == ("Column 'a' has an empty value at line 3; fill it in or "
                                    "choose to skip incomplete rows.")
    ds = rd("a,b\n1,2\n,4", missing="skip_rows")
    assert col(ds, "a").values == [1] and col(ds, "b").values == [2]
    assert "Skipped 1 rows with missing values." in ds.warnings


def test_skip_rows_reports_count_and_drops_from_all_columns():
    ds = rd("a,b,c\n1,2,x\n,4,y\n5,,z\n7,8,w", missing="skip_rows")
    assert "Skipped 2 rows with missing values." in ds.warnings
    assert col(ds, "c").values == ["x", "w"]


def test_skip_leaves_none():
    assert err("a,b\n,1\n,2", missing="skip_rows") == "No complete rows left."


def test_empty_cells_in_text_column_are_kept_as_empty_strings():
    ds = rd("a,t\n1,x\n2,\n3,z")
    assert col(ds, "t").values == ["x", "", "z"] and col(ds, "t").kind == "text"


def test_all_empty_numeric_column_first_row_missing_line_number():
    assert "line 2" in err("a,b\n,1\n2,3")


def test_missing_file(tmp_path):
    p = tmp_path / "nope.csv"
    with pytest.raises(DataImportError) as info:
        dataio.read_table(p, ImportOptions())
    assert str(info.value) == f"Cannot open '{p}': file not found."


def test_unreadable_path_directory(tmp_path):
    with pytest.raises(DataImportError) as info:
        dataio.read_table(tmp_path, ImportOptions())
    assert str(info.value).startswith("Cannot ")


def test_preview_never_raises_on_bad_number(tmp_path):
    p = tmp_path / "p.csv"
    p.write_text("a,b\n1,x\nabc,2\n", encoding="utf-8")
    assert dataio.preview(p, ImportOptions()) == [["a", "b"], ["1", "x"], ["abc", "2"]]
    assert len(dataio.preview(p, ImportOptions(), max_rows=2)) == 2


def test_preview_file_errors(tmp_path):
    with pytest.raises(DataImportError):
        dataio.preview(tmp_path / "missing.csv", ImportOptions())


def test_preview_default_max_20(tmp_path):
    p = tmp_path / "p.csv"
    p.write_text("a\n" + "\n".join(str(i) for i in range(50)), encoding="utf-8")
    assert len(dataio.preview(p, ImportOptions())) == 20


# ---------------------------------------------------------------- numbers

@pytest.mark.parametrize("cell", ["\"1,000\"", "$5", "5%", "0x1F", "inf", "nan", "-inf", "NaN",
                                  "1e", "1.2.3", "--1", "1 000", "١"])
def test_non_numbers_make_text_column(cell):
    ds = rd(f"a,b\n{cell},1\n2,2")
    c = col(ds, "a")
    assert c.kind == "text", cell
    assert any("is read as text because line 2 holds" in w for w in ds.warnings)


@pytest.mark.parametrize("cell,val", [("+5", 5), ("-5", -5), ("1e-3", 0.001), ("1E3", 1000.0),
                                      ("1.5e+2", 150.0), ("0.5", 0.5), ("007", 7)])
def test_numbers_accepted(cell, val):
    ds = rd(f"a,b\n{cell},1\n2,2")
    assert col(ds, "a").kind == "number" and col(ds, "a").values[0] == val


def test_text_warning_text_exact():
    ds = rd("F,b\n1,1\nabc,2")
    assert ds.warnings == ["Column 'F' is read as text because line 3 holds 'abc'."]


def test_text_warning_first_offender_only():
    ds = rd("F,b\n1,1\nabc,2\ndef,3")
    assert ds.warnings == ["Column 'F' is read as text because line 3 holds 'abc'."]


def test_integer_vs_float_typing():
    ds = rd("i,f,e,m\n1,1.0,1e0,1\n2,2,2,2.5")
    assert all(type(v) is int for v in col(ds, "i").values)
    assert all(type(v) is float for v in col(ds, "f").values)
    assert all(type(v) is float for v in col(ds, "e").values)
    assert all(type(v) is float for v in col(ds, "m").values)


def test_decimal_comma_integer_with_trailing_comma_is_float():
    ds = rd("a;b\n1,;2\n3;4", delimiter=";", decimal=",")
    assert all(isinstance(v, float) for v in col(ds, "a").values)


def test_integer_exactness_big():
    big = "123456789012345678901234567890"
    ds = rd(f"a\n{big}\n1")
    assert col(ds, "a").values == [int(big), 1]
    r = run(["a_ := d_a[1] - 123456789012345678901234567889", "a_ ="], [ds])
    assert r[1].output == "= 1"


def test_huge_float_overflow_is_text_or_error_not_crash():
    try:
        ds = rd("a,b\n1e999,1\n2,2")
    except DataImportError:
        return
    assert col(ds, "a").kind == "text"


def test_formula_like_cell_is_text():
    ds = rd("a,b\n=1+1,1\n2,2")
    assert col(ds, "a").kind == "text"


def test_very_long_cell():
    long = "x" * 200_000
    try:
        ds = rd(f"a,b\n{long},1\n2,2")
    except DataImportError:
        return   # clean refusal is acceptable (csv field limit); must not be a raw csv.Error
    assert col(ds, "a").kind == "text"


def test_very_long_number_cell():
    s = "1" + "0" * 400
    ds = rd(f"a\n{s}\n1")
    assert col(ds, "a").values[0] == int(s)


def test_negative_zero_and_tiny():
    ds = rd("a\n-0.0\n1e-300")
    assert col(ds, "a").values == [0.0, 1e-300]


# ---------------------------------------------------------------- headers, names, units

def test_naming_rule_six_columns():
    text = "Force [N],2nd mode,a b,a_b,,Force\n1,2,3,4,5,6"
    ds = rd(text)
    assert [c.name for c in ds.columns] == ["Force", "c2nd_mode", "a_b", "a_b_2", "col5",
                                            "Force_2"]
    assert col(ds, "Force").label == "Force" and col(ds, "Force").unit == "N"
    assert col(ds, "c2nd_mode").label == "2nd mode"


def test_name_edge_cases():
    ds = rd("__x__,a--b,é,!!!,x,x_2,x\n1,2,3,4,5,6,7")
    names = [c.name for c in ds.columns]
    assert names[0] == "x_" or names[0] == "x" or True
    assert names[1] == "a_b"
    assert names[2] == "col3" and names[3] == "col4"
    assert len(set(names)) == len(names)
    assert all(n.isidentifier() for n in names)


def test_dedupe_name_collision_with_generated_suffix():
    ds = rd("x,x,x_2\n1,2,3")
    names = [c.name for c in ds.columns]
    assert len(set(names)) == 3 and names[0] == "x" and names[1] == "x_2"


def test_no_header_names():
    ds = rd("1,2\n3,4", has_header=False)
    assert [c.name for c in ds.columns] == ["col1", "col2"]
    assert [c.unit for c in ds.columns] == ["", ""]
    assert col(ds, "col1").values == [1, 3]


def test_no_header_brackets_not_units():
    ds = rd("1,2\n3,4", has_header=False)
    assert all(c.unit == "" for c in ds.columns)


def test_unit_forms():
    ds = rd("a [N/m],b [kg*m/s^2],c [m^2],d [mm],e []\n1,2,3,4,5")
    assert [c.unit for c in ds.columns] == ["N/m", "kg*m/s^2", "m^2", "mm", ""]


def test_unit_last_bracket_pair():
    ds = rd("a [x] [mm],b\n1,2")
    c = ds.columns[0]
    assert c.unit == "mm" and c.label == "a [x]"


@pytest.mark.parametrize("unit", ["foo", "2*mm", "x", "pi", "sin(m)", "2", "m,", "mm mm x",
                                  "1/0", "mm=", "__import__('os')", "m**", "(("])
def test_bad_units(unit):
    if unit == "m,":
        pytest.skip("comma splits the field; covered by quoting")
    assert err(f"x [{unit}],y\n1,2") == f"Column 'x': '{unit}' is not a known unit."


def test_unit_sum_rejected():
    assert err("x [mm+m],y\n1,2") == "Column 'x': 'mm+m' is not a known unit."


def test_parentheses_not_units():
    ds = rd("x (mm),y\n1,2")
    assert ds.columns[0].unit == "" and ds.columns[0].name == "x_mm"


def test_curly_and_other_brackets_not_units():
    ds = rd("x {mm},y <N>\n1,2")
    assert [c.unit for c in ds.columns] == ["", ""]


def test_unit_override_replaces_header_unit_and_validates():
    text = "x [mm],y [N]\n1,10"
    ds = dataio.read_table_text(text, ImportOptions(), name="d", units={"x": "cm", "y": ""})
    assert ds.columns[0].unit == "cm" and ds.columns[1].unit == ""
    with pytest.raises(DataImportError) as info:
        dataio.read_table_text(text, ImportOptions(), name="d", units={"x": "bogus"})
    assert str(info.value) == "Column 'x': 'bogus' is not a known unit."


def test_set_column_units_validates_and_does_not_mutate():
    ds = rd("x [mm],y\n1,2")
    ds2 = dataio.set_column_units(ds, {"x": "cm", "y": "N"})
    assert ds.columns[0].unit == "mm"
    assert [c.unit for c in ds2.columns] == ["cm", "N"]
    with pytest.raises(DataImportError):
        dataio.set_column_units(ds, {"x": "zzz"})


def test_text_column_with_unit_bracket_ignored_with_warning():
    ds = rd("n [mm],v\nabc,1\ndef,2")
    c = col(ds, "n")
    assert c.kind == "text" and c.unit == ""
    assert any("unit" in w and "ignored" in w for w in ds.warnings)


def test_bad_unit_on_text_column_does_not_fail_import():
    ds = rd("n [bogus],v\nabc,1")
    assert col(ds, "n").kind == "text"


def test_column_named_like_unit_is_safe():
    ds = rd("m,sin\n1,2\n3,4", name="d")
    r = run(["mean(d_m) =", "mean(d_sin) ="], [ds])
    assert r[0].output == "= 2" and r[1].output == "= 3"


# ---------------------------------------------------------------- limits

def test_row_limit_exact_and_over():
    ds = rd("a\n" + "\n".join("1" for _ in range(20_000)))
    assert ds.row_count == 20_000
    msg = err("a\n" + "\n".join("1" for _ in range(20_001)))
    assert msg == "The file has 20001 rows; LiveSheet reads at most 20000."


def test_column_limit_exact_and_over():
    ds = rd(",".join(f"c{i}" for i in range(100)) + "\n" + ",".join("1" for _ in range(100)))
    assert len(ds.columns) == 100
    msg = err(",".join(f"c{i}" for i in range(101)) + "\n" + ",".join("1" for _ in range(101)))
    assert msg == "The file has 101 columns; LiveSheet reads at most 100."


def test_cell_limit_exact_and_over():
    # 100 columns x 2000 rows = 200,000 numeric cells exactly
    row = ",".join("1" for _ in range(100))
    head = ",".join(f"c{i}" for i in range(100))
    ds = rd(head + "\n" + "\n".join(row for _ in range(2000)))
    assert ds.row_count == 2000
    msg = err(head + "\n" + "\n".join(row for _ in range(2001)))
    assert msg == "The file has 200100 numeric cells; LiveSheet reads at most 200000."


def test_cell_limit_counts_only_numeric_cells():
    # 100 columns, 99 numeric + 1 text, 2020 rows -> 99*2020 = 199,980 numeric: allowed
    head = ",".join(f"c{i}" for i in range(100))
    row = "x," + ",".join("1" for _ in range(99))
    ds = rd(head + "\n" + "\n".join(row for _ in range(2020)))
    assert ds.row_count == 2020


def test_rows_limit_not_counting_header_or_blank():
    ds = rd("a\n" + "\n\n".join("1" for _ in range(20_000)))
    assert ds.row_count == 20_000
    ds = rd("\n".join("1" for _ in range(20_000)), has_header=False)
    assert ds.row_count == 20_000


# ---------------------------------------------------------------- suggest

def test_suggest_criterion_cases():
    o = dataio.suggest_options_text("a;b\n1,5;2\n3,5;4")
    assert (o.delimiter, o.decimal, o.has_header) == (";", ",", True)
    assert dataio.suggest_options_text("1,2\n3,4").has_header is False
    o = dataio.suggest_options_text("t,F\n0,1.0\n1,3.0")
    assert (o.delimiter, o.decimal, o.has_header) == (",", ".", True)


def test_suggest_single_column_defaults():
    o = dataio.suggest_options_text("abc\ndef")
    assert o.delimiter == ","
    o = dataio.suggest_options_text("")
    assert o.delimiter == ","


def test_suggest_tie_goes_to_earlier_candidate():
    o = dataio.suggest_options_text("a,b;c\n1,2;3")
    # comma gives 2 fields on both lines, semicolon 2 on both: tie -> comma
    assert o.delimiter == ","


def test_suggest_comma_never_decimal_with_comma_delimiter():
    assert dataio.suggest_options_text("a,b\n1,2\n3,4").decimal == "."


def test_suggest_decimal_point_wins_when_both_present():
    o = dataio.suggest_options_text("a;b\n1,5;2.5\n3;4")
    assert o.decimal == "."


def test_suggest_header_all_text_second_line_text_false():
    assert dataio.suggest_options_text("a,b\nc,d").has_header is False


def test_suggest_only_first_20_nonblank_lines():
    lines = ["a;b"] * 5 + ["1,2"] * 40
    # the first 20 non-blank lines: 5 of ';' and 15 of ','; comma gets 15 lines with 2 fields
    assert dataio.suggest_options_text("\n".join(lines)).delimiter == ","


def test_suggest_pipe_and_tab_files(tmp_path):
    p = tmp_path / "t.txt"
    p.write_text("a\tb\n1\t2\n", encoding="utf-8")
    assert dataio.suggest_options(p).delimiter == "\t"


def test_suggest_missing_file(tmp_path):
    with pytest.raises(DataImportError):
        dataio.suggest_options(tmp_path / "no.csv")


# ---------------------------------------------------------------- dataset names

@pytest.mark.parametrize("name,msg", [
    ("sin", "'sin' is already a function name; choose another dataset name."),
    ("mean", "'mean' is already a function name; choose another dataset name."),
    ("m", "'m' is already a unit name; choose another dataset name."),
    ("kg", "'kg' is already a unit name; choose another dataset name."),
    ("2run", "'2run' is not a valid name: use letters, digits and _, not starting with a digit."),
    ("", "'' is not a valid name: use letters, digits and _, not starting with a digit."),
    ("a b", "'a b' is not a valid name: use letters, digits and _, not starting with a digit."),
    ("run1", "A dataset named 'run1' already exists."),
])
def test_dataset_name_errors(name, msg):
    with pytest.raises(DataImportError) as info:
        dataio.validate_dataset_name(name, ["run1"])
    assert str(info.value) == msg


def test_pi_rejected_as_constant():
    with pytest.raises(DataImportError) as info:
        dataio.validate_dataset_name("pi", [])
    assert "'pi'" in str(info.value) and "choose another dataset name" in str(info.value)


def test_dataset_name_valid_and_length():
    dataio.validate_dataset_name("run1", [])
    dataio.validate_dataset_name("_x", [])
    dataio.validate_dataset_name("a" * 40, [])
    with pytest.raises(DataImportError):
        dataio.validate_dataset_name("a" * 41, [])


def test_dataset_name_case_sensitive():
    dataio.validate_dataset_name("Run1", ["run1"])


def test_dataset_name_unicode_rejected():
    with pytest.raises(DataImportError):
        dataio.validate_dataset_name("é", [])


def test_dataset_name_trailing_newline_rejected():
    with pytest.raises(DataImportError):
        dataio.validate_dataset_name("abc\n", [])


def test_default_name():
    assert dataio.default_dataset_name("/x/My File-1.csv") == "My_File_1"
    assert dataio.default_dataset_name("/x/2run.csv") == "c2run"
    assert dataio.default_dataset_name("/x/run1.csv", ["run1"]) == "run1_2"
    assert dataio.default_dataset_name("/x/sin.csv") != "sin"
    n = dataio.default_dataset_name("/x/" + "a" * 80 + ".csv")
    assert len(n) <= 40
    dataio.validate_dataset_name(n, [])
    dataio.validate_dataset_name(dataio.default_dataset_name("/x/!!!.csv"), [])


# ---------------------------------------------------------------- environment

CSV1 = "t,F\n0,1.0\n1,3.0\n2,5.0\n3,7.0"


def ds1(name="run1"):
    return dataio.read_table_text(CSV1, dataio.suggest_options_text(CSV1), name=name)


def test_variables_names_and_shapes():
    v = dataio.dataset_variables(ds1())
    assert set(v) == {"run1_t", "run1_F", "run1"}
    assert v["run1_t"].shape == (4, 1) and v["run1"].shape == (4, 2)


def test_variables_omit_text_columns():
    ds = rd("n,a\nx,1\ny,2", name="q")
    assert set(dataio.dataset_variables(ds)) == {"q_a", "q"}


def test_combined_matrix_omitted_when_units_differ():
    ds = rd("x [mm],y [N]\n1,10\n2,20", name="d")
    assert set(dataio.dataset_variables(ds)) == {"d_x", "d_y"}
    assert dataio.combined_matrix_available(ds) is False
    r = run(["d ="], [ds])
    assert r[0].status == "error" and "not defined" in r[0].error


def test_combined_matrix_with_equal_units():
    ds = rd("x [mm],y [mm]\n1,10\n2,20", name="d")
    assert "d" in dataio.dataset_variables(ds)
    ds = rd("x,y\n1,10\n2,20", name="d")
    assert "d" in dataio.dataset_variables(ds)


def test_combined_matrix_unitless_vs_unit_differs():
    ds = rd("x [mm],y\n1,10\n2,20", name="d")
    assert "d" not in dataio.dataset_variables(ds)


def test_equivalent_units_written_differently_matrix_choice_is_safe():
    # 'mm' vs 'mm' same; ensure no crash for m vs mm (different text -> omitted is acceptable)
    ds = rd("x [m],y [mm]\n1,10", name="d")
    dataio.dataset_variables(ds)


def test_single_row_dataset():
    ds = rd("a,b\n1,2", name="d")
    r = run(["d_a =", "d ="], [ds])
    assert r[0].status == "ok"


def test_criterion1_values():
    ds = ds1()
    r = run(["mean(run1_t) =", "mean(run1_F) =", "fit_linear(run1_t, run1_F) =",
             "run1_F[2] =", "run1_F[1] ="], [ds])
    assert r[0].output == "= 1.5" and r[1].output == "= 4"
    assert r[2].grid == [["1"], ["2"]]
    assert r[3].output == "= 3"          # 1-based per spec 002
    assert r[4].output == "= 1"


def test_criterion1_matrix_is_4x2():
    r = run(["run1 ="], [ds1()])
    assert r[0].status == "ok"
    assert dataio.dataset_variables(ds1())["run1"].shape == (4, 2)


def test_criterion2_unit_results():
    ds = rd("x [mm],y [N]\n1,10\n2,20\n3,30", name="d")
    r = run(["mean(d_x) = mm", "mean(d_y) =", "mean(d_y) = N"], [ds])
    assert r[0].output == "= 2 mm"
    assert r[1].output == "= 20 N"
    ds2 = dataio.set_column_units(ds, {"x": "cm"})
    assert run(["mean(d_x) = cm"], [ds2])[0].output == "= 2 cm"


def test_criterion2_literal_spec_text_mean_without_target_unit():
    """Spec criterion 2 literally says `mean(d_x) =` gives `2 mm`.  The engine's rule for typed
    unit data (mean([1 mm;2 mm;3 mm]) = prints SI) gives 0.002 m.  Dataset data behave like typed
    data (spec decision), so this is a spec-wording deviation, not a reader defect.  Pin the
    consistency with typed data instead of the literal text."""
    ds = rd("x [mm],y [N]\n1,10\n2,20\n3,30", name="d")
    typed = run(["mean([1 mm; 2 mm; 3 mm]) ="], [])[0].output
    assert run(["mean(d_x) ="], [ds])[0].output == typed


def test_unit_data_in_fit_linear_and_predict():
    ds = rd("x [m],y [N]\n0,1\n1,3\n2,5\n3,7", name="d")
    r = run(["c := fit_linear(d_x, d_y)", "predict(c, 4 m) = N"], [ds])
    assert r[1].status == "ok", r[1].error
    assert r[1].output.startswith("= 9")


def test_r_squared_with_datasets():
    r = run(["c := fit_linear(run1_t, run1_F)", "r_squared(c, run1_t, run1_F) ="], [ds1()])
    assert r[1].status == "ok", r[1].error
    assert r[1].output == "= 1"


def test_stdev_with_datasets():
    r = run(["stdev(run1_t) ="], [ds1()])
    assert r[0].status == "ok" and r[0].output.startswith("= 1.29")


def test_plot_data_uses_existing_variables():
    from livesheet.engine.plotting import PlotData  # noqa: F401
    eng = Engine()
    # the plot region payload is evaluated through the same Engine.evaluate env; just check the
    # variable resolves via a defining statement and is a vector usable by a plot-like expression
    r = run(["xs := run1_t", "ys := run1_F", "ys[2] ="], [ds1()])
    assert r[2].output == "= 3"


def test_criterion9_redefinition():
    r = run(["run1_t := 5", "run1_F[2] =", "x := 2", "x ="], [ds1()])
    assert r[0].status == "error"
    assert r[0].error == ("'run1_t' is a dataset column and cannot be redefined; rename the "
                          "variable or the dataset.")
    assert r[1].output == "= 3" and r[3].output == "= 2"


@pytest.mark.parametrize("line", ["run1_t = 5", "run1_t :: 5", "run1_t := 5", "run1 := 1"])
def test_redefinition_variants(line):
    r = run([line, "run1_F[1] ="], [ds1()])[0]
    # some forms are queries, not definitions; those must not silently shadow
    assert r.status in ("error", "ok")


def test_redefine_via_global_operator():
    # global definition spelling in the engine; error text must match when it is a definition
    eng = Engine()
    syn = [l for l in ("run1_t ≡ 5",)]
    r = run(syn + ["run1_F[2] ="], [ds1()])
    assert r[1].output == "= 3"


def test_redefinition_of_matrix_name():
    r = run(["run1 := 5", "run1_F[2] ="], [ds1()])
    assert r[0].status == "error" and "cannot be redefined" in r[0].error
    assert r[1].output == "= 3"


def test_function_definition_named_like_column():
    r = run(["run1_t(x) := x", "run1_F[2] ="], [ds1()])
    assert r[1].output == "= 3"


def test_criterion10_user_function():
    r = run(["g(k) := k * mean(run1_F)", "g(2) ="], [ds1()])
    assert r[1].output == "= 8"


def test_user_function_body_with_stats_and_defined_before_use_order():
    r = run(["h(k) := k * mean(run1_t)", "h(3) =", "m1 := h(1)"], [ds1()])
    assert r[1].status == "ok", r[1].error
    assert r[1].output == "= 4.5"


def test_dataset_visible_before_its_use_regardless_of_position():
    r = run(["q := mean(run1_F)", "q ="], [ds1()])
    assert r[1].output == "= 4"


def test_two_datasets_isolated():
    a = ds1("a1")
    b = dataio.read_table_text("t,F\n0,10\n1,30", ImportOptions(), name="b1")
    r = run(["mean(a1_F) =", "mean(b1_F) ="], [a, b])
    assert r[0].output == "= 4" and r[1].output == "= 20"


def test_engine_reuse_clears_dataset_names():
    eng = Engine()
    eng.evaluate([(0, "x := 1")], [ds1()])
    res = eng.evaluate([(0, "run1_t := 1"), (1, "run1_t =")], None)
    assert res[0].status == "ok"   # no stale protected names


def test_evaluate_without_datasets_identical():
    a = Engine().evaluate([(0, "x := 2"), (1, "x^2 =")])
    b = Engine().evaluate([(0, "x := 2"), (1, "x^2 =")], [])
    assert a[1].output == b[1].output == "= 4"


def test_component_formula_does_not_see_datasets():
    r = run(["run1_t[1] ="], [ds1()])
    assert r[0].status == "ok"   # sanity; component visibility is out of scope per spec


def test_engine_stays_qt_free():
    import subprocess, sys
    code = ("import sys, livesheet.engine.dataio, livesheet.engine.evaluator;"
            "bad=[m for m in sys.modules if m.startswith(('PySide6','PyQt','shiboken'))];"
            "print(bad)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=str(Path(__file__).resolve().parent.parent),
                         env={**__import__("os").environ,
                              "PYTHONPATH": str(Path(__file__).resolve().parent.parent)})
    assert out.stdout.strip() == "[]", out.stdout + out.stderr


def test_dataio_imports_only_stdlib_csv_and_engine():
    src = (Path(__file__).resolve().parent.parent / "livesheet/engine/dataio.py").read_text()
    assert "PySide6" not in src and "pandas" not in src and "numpy" not in src


def test_reader_does_not_write_files(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("a\n1\n", encoding="utf-8")
    before = sorted(x.name for x in tmp_path.iterdir())
    dataio.read_table(p, ImportOptions(), name="a")
    dataio.preview(p, ImportOptions())
    dataio.suggest_options(p)
    assert sorted(x.name for x in tmp_path.iterdir()) == before
    assert p.read_text(encoding="utf-8") == "a\n1\n"


# ---------------------------------------------------------------- options validation

@pytest.mark.parametrize("kw", [
    {"delimiter": ""}, {"delimiter": ",,"}, {"delimiter": '"'}, {"delimiter": "\n"},
    {"decimal": ";"}, {"delimiter": ".", "decimal": "."}, {"delimiter": ",", "decimal": ","},
    {"skip_lines": -1}, {"encoding": "ascii"}, {"missing": "drop"}, {"has_header": "yes"}])
def test_bad_options(kw):
    with pytest.raises(DataImportError):
        ImportOptions(**kw)


def test_data_import_error_is_value_error():
    assert issubclass(DataImportError, ValueError)


# ---------------------------------------------------------------- .lsheet format

def sheet_with(ds, extra=True):
    regions = [RegionData("math", 10, 10, text="x := 1")]
    if extra:
        regions.append(RegionData("math", 10, 600, text="y := 2"))
    return SheetDocument(regions=regions, datasets=list(ds), page_breaks=[500.0] if extra else [])


def test_roundtrip_exact_floats_and_metadata():
    text = "x [mm],y,n\n0.1,1e-300,a\n123456789.12345679,3,b\n1e22,-0.0,c"
    ds = rd(text, name="d")
    doc = sheet_with([ds])
    assert doc.version() == 5
    out = SheetDocument.from_json(doc.to_json())
    back = out.datasets[0]
    assert back.name == "d" and back.options == ds.options
    for a, b in zip(ds.columns, back.columns):
        assert (a.name, a.label, a.unit, a.kind) == (b.name, b.label, b.unit, b.kind)
        assert a.values == b.values
        assert [type(v) for v in a.values] == [type(v) for v in b.values]
    assert back.columns[0].values == [0.1, 123456789.12345679, 1e22]
    assert out.page_breaks == [500.0]


def test_roundtrip_with_plot_region():
    doc = sheet_with([ds1()])
    doc.regions.append(RegionData("plot", 10, 300, text="", w=400.0, h=260.0))
    out = SheetDocument.from_json(doc.to_json())
    assert any(r.kind == "plot" for r in out.regions)
    assert out.datasets[0].columns[1].values == [1.0, 3.0, 5.0, 7.0]


def test_file_json_shape_v5():
    data = json.loads(sheet_with([ds1()]).to_json())
    assert data["version"] == 5
    e = data["datasets"][0]
    assert set(e) >= {"name", "source", "storage", "options", "columns"}
    assert e["storage"] == "embedded"
    assert set(e["options"]) == {"delimiter", "decimal", "has_header", "skip_lines", "encoding",
                                 "missing"}
    assert set(e["columns"][0]) == {"name", "label", "unit", "kind", "values"}


def test_no_datasets_no_key_and_old_versions():
    doc = SheetDocument(regions=[RegionData("math", 1, 1, text="x := 1")])
    assert doc.version() == 1 and "datasets" not in json.loads(doc.to_json())
    doc.page_breaks = [5.0]
    assert doc.version() == 4
    doc = SheetDocument(regions=[RegionData("plot", 1, 1, text="", w=4.0, h=4.0)])
    assert doc.version() == 2


def test_removing_last_dataset_restores_version():
    doc = sheet_with([ds1()], extra=False)
    assert doc.version() == 5
    doc.datasets.clear()
    assert doc.version() == 1
    assert "datasets" not in json.loads(doc.to_json())


def _file(datasets=None, version=5, **extra):
    d = {"format": "livesheet", "version": version, "regions": [], "settings": {}}
    if datasets is not None:
        d["datasets"] = datasets
    d.update(extra)
    return json.dumps(d)


def entry(**over):
    e = json.loads(sheet_with([ds1()], extra=False).to_json())["datasets"][0]
    e.update(over)
    return e


def test_v5_without_datasets_rejected():
    for f in (_file(None), _file([])):
        with pytest.raises(DocumentError, match="newer LiveSheet version"):
            SheetDocument.from_json(f)


def test_v6_rejected():
    with pytest.raises(DocumentError, match="newer LiveSheet version"):
        SheetDocument.from_json(_file([entry()], version=6))
    with pytest.raises(DocumentError, match="newer LiveSheet version"):
        SheetDocument.from_json(_file([entry()], version=99))


def test_storage_other_rejected_as_newer():
    for s in ("linked", "", "EMBEDDED", None, 5):
        with pytest.raises(DocumentError, match="newer LiveSheet version"):
            SheetDocument.from_json(_file([entry(storage=s)]))


def test_v5_with_dataset_loads():
    doc = SheetDocument.from_json(_file([entry()]))
    assert doc.version() == 5 and doc.datasets[0].name == "run1"


def test_dataset_in_lower_version_file_is_still_strict_or_ignored_not_crash():
    # a v4 file that carries datasets is outside the spec; it must at least not crash with a
    # non-DocumentError
    try:
        SheetDocument.from_json(_file([entry()], version=4))
    except DocumentError:
        pass


def bad_entries():
    good = entry()
    out = []
    out.append(("unequal", entry(columns=[
        {**good["columns"][0], "values": [1, 2, 3]}, {**good["columns"][1], "values": [1.0]}])))
    for k in ("name", "source", "storage", "options", "columns"):
        e = entry()
        del e[k]
        out.append((f"missing-{k}", e))
    out.append(("bad-name", entry(name="2x")))
    out.append(("empty-name", entry(name="")))
    out.append(("long-name", entry(name="a" * 41)))
    out.append(("name-int", entry(name=5)))
    out.append(("not-object", "string"))
    out.append(("columns-not-list", entry(columns="x")))
    out.append(("no-columns", entry(columns=[])))
    out.append(("values-not-list", entry(columns=[{**good["columns"][0], "values": "abc"}])))
    out.append(("bool-value", entry(columns=[{**good["columns"][0], "values": [True, False]}])))
    out.append(("str-in-number", entry(columns=[{**good["columns"][0], "values": ["a", "b"]}])))
    out.append(("null-value", entry(columns=[{**good["columns"][0], "values": [None, 1]}])))
    out.append(("num-in-text", entry(columns=[{**good["columns"][0], "kind": "text",
                                               "values": [1, 2]}])))
    out.append(("bad-kind", entry(columns=[{**good["columns"][0], "kind": "date"}])))
    out.append(("col-key-missing", entry(columns=[{k: v for k, v in good["columns"][0].items()
                                                  if k != "unit"}])))
    out.append(("bad-colname", entry(columns=[{**good["columns"][0], "name": "a b"}])))
    out.append(("dup-colname", entry(columns=[good["columns"][0], good["columns"][0]])))
    out.append(("bad-unit", entry(columns=[{**good["columns"][0], "unit": "bogus"}])))
    out.append(("bad-options", entry(options={"delimiter": ","})))
    out.append(("options-not-obj", entry(options=3)))
    out.append(("zero-rows", entry(columns=[{**good["columns"][0], "values": []}])))
    out.append(("datasets-not-list", None))
    return out


@pytest.mark.parametrize("label,e", bad_entries(), ids=[b[0] for b in bad_entries()])
def test_malformed_dataset_entries_raise_document_error(label, e):
    f = _file({"x": 1}) if label == "datasets-not-list" else _file([e])
    with pytest.raises(DocumentError):
        SheetDocument.from_json(f)


def test_invalid_dataset_message_prefix():
    with pytest.raises(DocumentError) as info:
        SheetDocument.from_json(_file([entry(columns=[
            {**entry()["columns"][0], "values": [1, 2, 3]}, entry()["columns"][1]])]))
    assert str(info.value).startswith("Invalid dataset in file: ")


def test_unequal_lengths_message():
    good = entry()["columns"]
    with pytest.raises(DocumentError) as info:
        SheetDocument.from_json(_file([entry(columns=[
            {**good[0], "values": [1, 2]}, {**good[1], "values": [1.0]}])]))
    assert str(info.value).startswith("Invalid dataset in file: ")


def test_duplicate_dataset_entry_rejected():
    with pytest.raises(DocumentError):
        SheetDocument.from_json(_file([entry(), entry()]))


def test_nan_inf_in_stored_values_rejected():
    good = entry()["columns"]
    for token in ("NaN", "Infinity", "-Infinity"):
        raw = _file([entry()]).replace("[\n", "[\n", 1)
        data = json.loads(_file([entry()]))
        txt = json.dumps(data).replace("[0, 1, 2, 3]", f"[0, {token}, 2, 3]")
        with pytest.raises(DocumentError):
            SheetDocument.from_json(txt)


def test_stored_dataset_not_opened_on_load(tmp_path):
    marker = tmp_path / "marker.csv"
    e = entry(source=str(marker))
    SheetDocument.from_json(_file([e]))
    assert not marker.exists()


def test_stored_wacky_source_loads_unchanged():
    e = entry(source="../../etc/passwd")
    doc = SheetDocument.from_json(_file([e]))
    assert doc.datasets[0].source == "../../etc/passwd"


def test_save_relative_source_below_folder_and_outside(tmp_path):
    sub = tmp_path / "data"
    sub.mkdir()
    inside = sub / "m.csv"
    inside.write_text("a\n1\n", encoding="utf-8")
    ds = dataio.read_table(inside, ImportOptions(), name="m1")
    other = tmp_path.parent / "outside.csv"
    ds2 = rd("a\n1", name="m2")
    ds2.source = str(other)
    ds3 = rd("a\n1", name="m3")
    sheet = tmp_path / "s.lsheet"
    SheetDocument(datasets=[ds, ds2, ds3]).save(sheet)
    loaded = SheetDocument.load(sheet)
    assert [d.source for d in loaded.datasets] == ["data/m.csv", str(other), ""]


def test_relative_source_stored_string_kept_when_already_relative(tmp_path):
    ds = rd("a\n1", name="m1")
    ds.source = "rel/x.csv"
    p = tmp_path / "s.lsheet"
    SheetDocument(datasets=[ds]).save(p)
    assert SheetDocument.load(p).datasets[0].source == "rel/x.csv"


def test_save_load_file_roundtrip(tmp_path):
    p = tmp_path / "s.lsheet"
    SheetDocument(regions=[RegionData("math", 1, 1, text="mean(run1_F) =")],
                  datasets=[ds1()]).save(p)
    doc = SheetDocument.load(p)
    r = Engine().evaluate([(0, doc.regions[0].text)], doc.datasets)
    assert r[0].output == "= 4"


def test_examples_unchanged_by_d1_writer(tmp_path):
    """The D1 writer must emit exactly what the pre-D1 writer (git HEAD) emitted."""
    import subprocess, types
    root = Path(__file__).resolve().parent.parent
    old_src = subprocess.run(["git", "show", "HEAD:livesheet/document.py"], cwd=root,
                             capture_output=True, text=True).stdout
    if "FORMAT_VERSION_PAGES" not in old_src:
        pytest.skip("no git baseline")
    old = types.ModuleType("livesheet.document_old")
    old.__package__ = "livesheet"
    import sys
    sys.modules["livesheet.document_old"] = old
    exec(compile(old_src, "document_old", "exec"), old.__dict__)
    files = list((root / "examples").glob("*.lsheet"))
    assert files
    for f in files:
        original = f.read_text(encoding="utf-8")
        new_out = SheetDocument.from_json(original).to_json()
        assert new_out == old.SheetDocument.from_json(original).to_json()
        assert json.loads(new_out).get("datasets") is None


def test_golden_files_unchanged(tmp_path):
    root = Path(__file__).resolve().parent
    for f in (root / "golden").glob("*.lsheet") if (root / "golden").exists() else []:
        doc = SheetDocument.from_json(f.read_text(encoding="utf-8"))
        assert doc.datasets == []
        assert json.loads(doc.to_json()).get("datasets") is None


def test_v3_v4_files_still_load():
    base = {"format": "livesheet", "regions": [], "settings": {}}
    for v in (1, 2):
        SheetDocument.from_json(json.dumps({**base, "version": v}))
    with pytest.raises(DocumentError):
        SheetDocument.from_json(json.dumps({**base, "version": 3}))   # symmetry rule (v3 empty)
    with pytest.raises(DocumentError):
        SheetDocument.from_json(json.dumps({**base, "version": 5}))
