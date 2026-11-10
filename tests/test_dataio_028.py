"""Spec 028 phase D1: delimited-text reader, evaluator seeding and the version-5 file format."""

import json
from pathlib import Path

import pytest
import sympy as sp

from livesheet.document import DocumentError, RegionData, SheetDocument
from livesheet.engine import dataio
from livesheet.engine.dataio import DataImportError, ImportOptions
from livesheet.engine.evaluator import Engine

CSV1 = "t,F\n0,1.0\n1,3.0\n2,5.0\n3,7.0"


def read(text, name="d", **kw):
    opts = kw.pop("options", None) or dataio.suggest_options_text(text)
    return dataio.read_table_text(text, opts, name=name, **kw)


def run(lines, datasets):
    res = Engine().evaluate([(i, s) for i, s in enumerate(lines)], datasets)
    return [res[i] for i in range(len(lines))]


def err(text, **kw):
    with pytest.raises(DataImportError) as info:
        read(text, **kw)
    return str(info.value)


def test_criterion1_linear_fit_and_stats():
    opts = dataio.suggest_options_text(CSV1)
    assert opts.delimiter == "," and opts.has_header and opts.decimal == "."
    ds = dataio.read_table_text(CSV1, opts, name="run1")
    t, f = ds.columns
    assert all(isinstance(v, int) for v in t.values)
    assert all(isinstance(v, float) for v in f.values)
    r = run(["mean(run1_t) =", "mean(run1_F) =", "fit_linear(run1_t, run1_F) =",
             "run1_F[2] =", "run1 ="], [ds])
    assert r[0].output == "= 1.5"
    assert r[1].output == "= 4"
    assert r[2].grid == [["1"], ["2"]]
    assert r[3].status == "ok" and r[3].output in ("= 3", "= 5")   # index base per spec 002
    assert r[4].status == "ok" and r[4].grid == [] and "4" in r[4].output or r[4].grid
    assert dataio.dataset_variables(ds)["run1"].shape == (4, 2)


def test_criterion2_units():
    ds = read("x [mm],y [N]\n1,10\n2,20\n3,30", name="d")
    assert [(c.name, c.label, c.unit) for c in ds.columns] == [("x", "x", "mm"), ("y", "y", "N")]
    # Output units follow the engine rule for typed data (SI unless a unit is requested).
    r = run(["mean(d_x) = mm", "mean(d_y) =", "d ="], [ds])
    assert r[0].output == "= 2 mm" and r[1].output == "= 20 N"
    assert run(["mean(d_x) ="], [ds])[0].output == "= 0.002 m"
    assert r[2].status == "error" and "not defined" in r[2].error
    ds2 = dataio.set_column_units(ds, {"x": "cm"})
    assert run(["mean(d_x) = cm"], [ds2])[0].output == "= 2 cm"
    assert err("x [foo],y\n1,2") == "Column 'x': 'foo' is not a known unit."
    assert "not a known unit" in err("x [3 m],y\n1,2")
    assert read("a [N/m],b [kg*m/s^2]\n1,2").columns[1].unit == "kg*m/s^2"


def test_unit_override_at_read():
    ds = read("x [mm]\n1\n2", units={"x": "cm"})
    assert ds.columns[0].unit == "cm"


def test_criterion3_decimal_comma():
    text = "a;b\n1,5;2\n3,5;4"
    opts = dataio.suggest_options_text(text)
    assert (opts.delimiter, opts.decimal, opts.has_header) == (";", ",", True)
    ds = dataio.read_table_text(text, opts, name="d")
    assert ds.columns[0].values == [1.5, 3.5] and ds.columns[1].values == [2, 4]
    assert dataio.dataset_variables(ds)["d_a"] == sp.Matrix([1.5, 3.5])
    forced = dataio.read_table_text(text, ImportOptions(";", ".", True), name="d")
    assert forced.columns[0].kind == "text"
    assert "Column 'a' is read as text because line 2 holds '1,5'." in forced.warnings
    assert "d_a" not in dataio.dataset_variables(forced)


def test_criterion4_no_header():
    text = "1,2\n3,4"
    assert dataio.suggest_options_text(text).has_header is False
    ds = dataio.read_table_text(text, ImportOptions(has_header=False), name="d")
    assert [c.name for c in ds.columns] == ["col1", "col2"]


def test_criterion5_naming():
    text = "Force [N],2nd mode,a b,a_b,,Force\n1,2,3,4,5,6"
    ds = read(text)
    assert [c.name for c in ds.columns] == ["Force", "c2nd_mode", "a_b", "a_b_2", "col5",
                                            "Force_2"]
    assert [c.label for c in ds.columns][:2] == ["Force", "2nd mode"]
    assert ds.columns[0].unit == "N"


def test_criterion6_quoting():
    ds = read('"name, full",v\n"a,b",1')
    assert [c.kind for c in ds.columns] == ["text", "number"]
    assert ds.columns[0].values == ["a,b"]


def test_criterion7_errors():
    assert err("a,b\n1,2\n3") == "Line 3 has 1 field, but the first line has 2."
    assert err("a,b\n1,2\n,4") == ("Column 'a' has an empty value at line 3; fill it in or "
                                    "choose to skip incomplete rows.")
    ds = read("a,b\n1,2\n,4", options=ImportOptions(missing="skip_rows"))
    assert ds.row_count == 1 and "Skipped 1 rows with missing values." in ds.warnings
    assert err("a,b", options=ImportOptions()) == "The file has no data rows."
    assert err("a,b\nx,y") == "The file has no numeric column."
    assert err("a,b\n,\n,", options=ImportOptions(missing="skip_rows")) == "No complete rows left."
    assert err("") == "The file has no data rows."


def test_file_errors(tmp_path):
    missing = tmp_path / "nope.csv"
    with pytest.raises(DataImportError, match="Cannot open .*nope.csv.: file not found."):
        dataio.read_table(missing)
    with pytest.raises(DataImportError, match="Cannot read"):
        dataio.read_table(tmp_path)
    p = tmp_path / "l.csv"
    p.write_bytes("a,b\n1,caf\xe9\n".encode("latin-1"))
    with pytest.raises(DataImportError, match="not valid UTF-8 text; try the Latin-1"):
        dataio.read_table(p)
    assert dataio.suggest_options(p).encoding == "latin-1"
    ds = dataio.read_table(p, ImportOptions(encoding="latin-1"), name="l")
    assert ds.columns[1].values == ["caf\xe9"]
    assert ds.source == str(p)


def test_bom_crlf_skip_lines_and_preview(tmp_path):
    p = tmp_path / "b.csv"
    p.write_bytes("﻿junk line\r\nx,y\r\n\r\n1,2\r\n3,4\r\n".encode("utf-8"))
    opts = dataio.suggest_options(p)
    assert opts.delimiter == "," and opts.skip_lines == 0
    ds = dataio.read_table(p, ImportOptions(skip_lines=1), name="b")
    assert [c.name for c in ds.columns] == ["x", "y"] and ds.columns[0].values == [1, 3]
    assert dataio.preview(p, ImportOptions(skip_lines=1), max_rows=2) == [["x", "y"], ["1", "2"]]
    assert dataio.preview(p, ImportOptions(skip_lines=1))[-1] == ["3", "4"]
    # error lines refer to physical file lines
    with pytest.raises(DataImportError, match="Line 4 has"):
        dataio.read_table_text("pre\nx,y\n1,2\n3", ImportOptions(skip_lines=1))


def test_limits():
    rows = "\n".join(str(i) for i in range(20001))
    assert err("x\n" + rows) == "The file has 20001 rows; LiveSheet reads at most 20000."
    assert read("x\n" + "\n".join(str(i) for i in range(20000))).row_count == 20000
    wide = ",".join(f"c{i}" for i in range(101))
    assert "101 columns; LiveSheet reads at most 100" in err(wide + "\n" + ",".join("1" * 101))
    cols = ",".join(f"c{i}" for i in range(20))
    line = ",".join("1" * 20)
    assert "numeric cells; LiveSheet reads at most 200000" in err(
        cols + "\n" + "\n".join([line] * 10001))


def test_number_syntax():
    ds = read("a,b,c,d\n1e-3,+2,-.5,5.\n2,3,4,5")
    assert ds.columns[0].values == [0.001, 2.0] and ds.columns[1].values == [2, 3]
    for bad in ("1,000", "$5", "5%", "inf", "nan", "0x10", "1e999"):
        d = read(f"a;b\n{bad};1\n2;2", options=ImportOptions(";", "."))
        assert d.columns[0].kind == "text", bad


def test_text_column_unit_ignored_with_warning():
    ds = read("n [mm],v\nabc,1\ndef,2")
    assert ds.columns[0].kind == "text" and ds.columns[0].unit == ""
    assert any("unit" in w for w in ds.warnings)


def test_options_validation():
    for kwargs in ({"delimiter": ""}, {"delimiter": ";;"}, {"delimiter": '"'}, {"decimal": ";"},
                   {"delimiter": ",", "decimal": ","}, {"skip_lines": -1}, {"encoding": "x"},
                   {"missing": "x"}):
        with pytest.raises(DataImportError):
            ImportOptions(**kwargs)


def test_suggest_delimiters():
    assert dataio.suggest_options_text("a\tb\n1\t2\n3\t4").delimiter == "\t"
    assert dataio.suggest_options_text("a|b\n1|2").delimiter == "|"
    assert dataio.suggest_options_text("a\n1\n2").delimiter == ","
    assert dataio.suggest_options_text("a,b\n1.5,2").decimal == "."


def test_dataset_names():
    for name, text in [("sin", "sin is already a function name"), ("m", "already a unit name"),
                       ("pi", "'pi' is already a constant name"),
                       ("2run", "'2run' is not a valid name: use letters, digits and _, not "
                                "starting with a digit."),
                       ("", "not a valid name"), ("x" * 41, "at most 40"),
                       ("run1", "A dataset named 'run1' already exists.")]:
        with pytest.raises(DataImportError) as info:
            dataio.validate_dataset_name(name, ["run1"])
        assert text.replace("sin is", "'sin' is") in str(info.value) or text in str(info.value)
    assert "'sin' is already a function name; choose another dataset name." in _msg("sin")
    dataio.validate_dataset_name("run1", ["other"])
    dataio.validate_dataset_name("x" * 40)
    assert dataio.default_dataset_name("/tmp/my data-1.csv", []) == "my_data_1"
    assert dataio.default_dataset_name("2020.csv", []) == "c2020"
    assert dataio.default_dataset_name("a.csv", ["a"]) == "a_2"
    assert dataio.default_dataset_name("m.csv", []) == "m_2"


def _msg(name):
    try:
        dataio.validate_dataset_name(name)
    except DataImportError as exc:
        return str(exc)
    return ""


def test_criterion9_redefinition():
    ds = read(CSV1, name="run1")
    r = run(["run1_t := 5", "run1_t ≡ 6", "x := 2", "x + 1 ="], [ds])
    msg = "'run1_t' is a dataset column and cannot be redefined; rename the variable or the dataset."
    assert r[0].status == "error" and r[0].error == msg
    assert r[1].error == msg
    assert r[3].output == "= 3"
    assert run(["mean(run1_t) ="], [ds])[0].output == "= 1.5"


def test_criterion10_user_function():
    ds = read(CSV1, name="run1")
    r = run(["g(k) := k * mean(run1_F)", "g(2) ="], [ds])
    assert r[1].output == "= 8"


def test_evaluate_without_datasets_unchanged():
    assert Engine().evaluate([(0, "1+1 =")])[0].output == "= 2"


def test_two_datasets_and_same_unit_matrix():
    a = read("p [m],q [m]\n1,2\n3,4", name="a")
    b = read("u\n10\n20", name="b")
    r = run(["a =", "mean(b_u) ="], [a, b])
    assert r[0].status == "ok" and r[1].output == "= 15"


# -- file format --------------------------------------------------------------

def test_criterion11_roundtrip_and_versions():
    ds = read("a [mm],b,c\n0.1,1e-300,x\n123456789.12345679,2,y", name="run1")
    doc = SheetDocument(
        regions=[RegionData("math", 0.0, 0.0, "mean(run1_a) =")], page_breaks=[500.0],
        datasets=[ds])
    doc.regions.append(RegionData("plot", 0.0, 100.0, "x"))
    assert doc.version() == 5
    text = doc.to_json()
    data = json.loads(text)
    assert data["version"] == 5 and data["datasets"][0]["storage"] == "embedded"
    back = SheetDocument.from_json(text)
    assert back.page_breaks == [500.0]
    assert any(r.kind == "plot" for r in back.regions)
    got = back.datasets[0]
    assert [(c.name, c.label, c.unit, c.kind) for c in got.columns] == \
        [(c.name, c.label, c.unit, c.kind) for c in ds.columns]
    assert got.columns[0].values == ds.columns[0].values == [0.1, 123456789.12345679]
    assert got.columns[1].values == [1e-300, 2.0]
    assert isinstance(got.columns[0].values[0], float)
    assert got.options == ds.options and got.name == "run1"
    assert back.to_json() == text
    back.datasets.clear()
    assert back.version() == 4
    doc.datasets.clear(); doc.page_breaks.clear()
    assert doc.version() == 2 and "datasets" not in doc.to_json()


def test_no_datasets_shape_unchanged():
    doc = SheetDocument(regions=[RegionData("math", 0, 0, "1+1 =")])
    data = json.loads(doc.to_json())
    assert data["version"] == 1 and "datasets" not in data


def _file(datasets=None, version=5):
    data = {"format": "livesheet", "version": version, "settings": {"significant": 6},
            "regions": []}
    if datasets is not None:
        data["datasets"] = datasets
    return json.dumps(data)


def _entry(**over):
    e = {"name": "d", "source": "", "storage": "embedded",
         "options": ImportOptions().to_dict(),
         "columns": [{"name": "x", "label": "x", "unit": "", "kind": "number",
                      "values": [1, 2.5]}]}
    e.update(over)
    return e


def test_format_rejections():
    newer = "newer LiveSheet version"
    with pytest.raises(DocumentError, match=newer):
        SheetDocument.from_json(_file())
    with pytest.raises(DocumentError, match=newer):
        SheetDocument.from_json(_file([]))
    with pytest.raises(DocumentError, match=newer):
        SheetDocument.from_json(_file([_entry()], version=6))
    with pytest.raises(DocumentError, match=newer):
        SheetDocument.from_json(_file([_entry(storage="linked")]))
    assert SheetDocument.from_json(_file([_entry()])).datasets[0].name == "d"


@pytest.mark.parametrize("entry", [
    "notadict",
    {"name": "d"},
    _entry(name="2bad"),
    _entry(options={"delimiter": ","}),
    _entry(columns=[]),
    _entry(columns=[{"name": "x", "label": "x", "unit": "", "kind": "number", "values": [1]},
                    {"name": "y", "label": "y", "unit": "", "kind": "number", "values": [1, 2]}]),
    _entry(columns=[{"name": "x", "label": "x", "unit": "", "kind": "number", "values": ["a"]}]),
    _entry(columns=[{"name": "x", "label": "x", "unit": "", "kind": "number", "values": [True]}]),
    _entry(columns=[{"name": "x", "label": "x", "unit": "foo", "kind": "number", "values": [1]}]),
    _entry(columns=[{"name": "x", "label": "x", "unit": "", "kind": "text", "values": [1]}]),
    _entry(columns=[{"name": "x", "label": "x", "unit": "", "kind": "text", "values": ["a"]}]),
    _entry(columns=[{"name": "x", "label": "x", "kind": "number", "values": [1]}]),
])
def test_invalid_dataset_fails_load(entry):
    with pytest.raises(DocumentError, match="Invalid dataset in file: "):
        SheetDocument.from_json(_file([entry]))


def test_duplicate_dataset_names_rejected():
    with pytest.raises(DocumentError, match="Invalid dataset in file"):
        SheetDocument.from_json(_file([_entry(), _entry()]))


def test_source_relative_when_below_sheet_folder(tmp_path):
    inside = tmp_path / "data" / "m.csv"
    inside.parent.mkdir()
    inside.write_text("x\n1\n")
    outside = tmp_path.parent / "elsewhere.csv"
    a = dataio.read_table(inside, name="a")
    b = dataio.read_table_text("x\n1", name="b", source=str(outside))
    c = dataio.read_table_text("x\n1", name="c", source="")
    sheet = tmp_path / "s.lsheet"
    SheetDocument(datasets=[a, b, c]).save(sheet)
    loaded = SheetDocument.load(sheet)
    assert [d.source for d in loaded.datasets] == ["data/m.csv", str(outside), ""]
    assert a.source == str(inside)   # saving does not mutate the in-memory dataset


def test_existing_files_and_examples_unchanged(tmp_path):
    root = Path(__file__).resolve().parent.parent
    files = list((root / "examples").glob("*.lsheet"))
    assert files
    for f in files:
        original = f.read_text(encoding="utf-8")
        doc = SheetDocument.from_json(original)
        assert doc.datasets == [] and doc.version() <= 4
        out = tmp_path / f.name
        doc.save(out)
        again = SheetDocument.load(out)
        assert again.to_json() == doc.to_json()
        assert json.loads(out.read_text(encoding="utf-8")).get("datasets") is None
