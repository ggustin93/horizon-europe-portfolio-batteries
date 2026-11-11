from pathlib import Path

import pandas as pd
import pytest

import cordis

FIXTURE = Path(__file__).parent / "fixtures" / "project_sample.csv"


def test_unparseable_rows_are_counted_and_excluded():
    df, excluded = cordis.read_cordis_csv(FIXTURE)
    assert excluded == 1
    assert df["acronym"].tolist() == ["GOOD", "OK"]


def test_money_columns_are_read_as_numbers_with_decimal_comma():
    df, _ = cordis.read_cordis_csv(FIXTURE)
    assert df["ecMaxContribution"].tolist() == [2073781.25, 1000000.0]
    assert df["ecMaxContribution"].sum() == 3073781.25


def test_checksum_mismatch_warns_but_returns_the_file(tmp_path):
    (tmp_path / "x.zip").write_bytes(b"not the published file")
    (tmp_path / "SHA256SUMS").write_text("0" * 64 + "  x.zip\n")
    with pytest.warns(UserWarning, match="SHA-256"):
        path = cordis.fetch_zip("x.zip", raw_dir=tmp_path, sums_file=tmp_path / "SHA256SUMS")
    assert path == tmp_path / "x.zip"


def test_keyword_rule_depends_on_the_fields_searched():
    df, _ = cordis.read_cordis_csv(FIXTURE)
    assert cordis.matches_terms(df, ["battery"], ["title"]).tolist() == [True, False]
    assert cordis.matches_terms(df, ["OBJECTIVE"], ["title"]).tolist() == [False, False]
    assert cordis.matches_terms(df, ["objective"], ["title", "objective"]).tolist() == [True, True]


def pool():
    return pd.DataFrame(
        {
            "id": range(1, 11),
            "ecMaxContribution": [5.0, 1.0, 9.0, 2.0, 8.0, 3.0, 7.0, 4.0, 6.0, 10.0],
            "ambiguous": [True, True, False, False, False, False, False, False, False, False],
            "single": [True, True, True, True, True, True, True, True, False, False],
        }
    )


def test_sample_strata_are_disjoint_drawn_in_order_and_reproducible():
    df = pool()
    strata = [
        ("other sense", df["ambiguous"], 1, None),
        ("single mention, top funded", df["single"], 2, "ecMaxContribution"),
        ("single mention, random", df["single"], 2, None),
    ]
    first = cordis.draw_sample(df, strata, seed=1)
    again = cordis.draw_sample(df.sample(frac=1, random_state=7), strata, seed=1)  # row order must not matter

    assert first["id"].tolist() == again["id"].tolist()
    assert first["stratum"].value_counts().to_dict() == {
        "other sense": 1,
        "single mention, top funded": 2,
        "single mention, random": 2,
    }
    assert first["id"].is_unique
    top = set(first.loc[first["stratum"] == "single mention, top funded", "id"])
    assert top == {3, 5}  # the two largest contributions among single mentions not already drawn
    assert not top & set(first.loc[first["stratum"] == "other sense", "id"])


def test_agreement_is_counted_per_stratum_and_in_total():
    labelled = pd.DataFrame(
        {
            "stratum": ["grey", "grey", "grey", "grey", "miss", "miss"],
            "label": ["central", "none", "unsure", "", "none", "contributes"],
            "rule": [True, True, True, True, False, False],
        }
    )
    counts = cordis.agreement(labelled)
    assert counts.loc["grey"].to_dict() == {"projects": 4, "labelled": 3, "agree": 1, "disagree": 1, "unsure": 1}
    assert counts.loc["miss"].to_dict() == {"projects": 2, "labelled": 2, "agree": 1, "disagree": 1, "unsure": 0}
    assert counts.loc["total"].to_dict() == {"projects": 6, "labelled": 5, "agree": 2, "disagree": 2, "unsure": 1}


def test_unknown_label_is_rejected_and_named():
    with pytest.raises(ValueError, match="yes"):
        cordis.agreement(pd.DataFrame({"stratum": ["grey"], "label": ["yes"], "rule": [True]}))


def test_annotation_sheet_is_written_once_and_never_overwritten(tmp_path):
    path = tmp_path / "sample.csv"
    cordis.write_once(pd.DataFrame({"id": [1], "label": [""]}), path)
    path.write_text("id,label\n1,central\n")  # the annotator's answers
    cordis.write_once(pd.DataFrame({"id": [2], "label": [""]}), path)
    assert path.read_text() == "id,label\n1,central\n"


def test_stratum_short_of_candidates_fails_loudly():
    df = pool()
    with pytest.raises(ValueError, match="other sense"):
        cordis.draw_sample(df, [("other sense", df["ambiguous"], 3, None)], seed=1)


def test_model_answer_is_reduced_to_one_of_the_four_labels():
    assert cordis.parse_label("Central") == "central"
    assert cordis.parse_label('"none"\nThe project will use a battery of tests.') == "none"
    assert cordis.parse_label("Label: contributes.\nRecycled black mass is the feedstock.") == "contributes"
    assert cordis.parse_label("I cannot tell from this abstract.") == "unsure"
    assert cordis.evidence("none\nThe project will use a battery of tests.") == "The project will use a battery of tests."
    assert cordis.evidence("central") == ""


def test_row_level_agreement_with_a_yes_no_prediction():
    label = pd.Series(["central", "contributes", "none", "unsure", ""])
    predicted = pd.Series([True, False, False, True, True])
    assert cordis.agrees(label, predicted).tolist() == [True, False, True, None, None]


def test_model_call_sends_title_and_objective_and_returns_the_answer():
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    seen = {}

    class Fake(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["path"] = self.path
            seen["auth"] = self.headers["Authorization"]
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            reply = json.dumps({"choices": [{"message": {"content": "contributes"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(reply)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        answer = cordis.ask_model("Battery recycling", "Objective text.", "k", f"http://127.0.0.1:{server.server_port}/v1", "m")
    finally:
        server.shutdown()
        server.server_close()
    assert answer == "contributes"
    assert seen["path"] == "/v1/chat/completions" and seen["auth"] == "Bearer k"
    assert seen["body"]["model"] == "m" and "Battery recycling" in seen["body"]["messages"][1]["content"]
    assert seen["body"]["messages"][0]["content"] == cordis.QUESTION


def test_model_call_waits_and_retries_when_the_provider_says_too_many_requests(monkeypatch):
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    calls, waits = [], []
    monkeypatch.setattr(cordis.time, "sleep", waits.append)

    class Fake(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            calls.append(1)
            reply = json.dumps({"choices": [{"message": {"content": "none"}}]}).encode()
            self.send_response(429 if len(calls) == 1 else 200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(reply)))
            self.end_headers()
            self.wfile.write(reply)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        answer = cordis.ask_model("T", "O", "k", f"http://127.0.0.1:{server.server_port}/v1", "m")
    finally:
        server.shutdown()
        server.server_close()
    assert answer == "none" and len(calls) == 2 and waits == [5]
