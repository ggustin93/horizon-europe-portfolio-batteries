"""Fetch and read CORDIS Horizon Europe CSV exports.

CORDIS publishes its CSV files with ';' as separator, every field quoted and a
decimal comma in money columns. A few hundred rows contain an unescaped quote
in the free-text columns and cannot be parsed: they are counted and excluded,
never repaired.
"""

import hashlib
import json
import string
import time
import warnings
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen, urlretrieve

import pandas as pd

BASE_URL = "https://cordis.europa.eu/data/"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA_DIR / "raw"
SUMS_FILE = DATA_DIR / "SHA256SUMS"


def fetch_zip(name, raw_dir=RAW_DIR, sums_file=SUMS_FILE):
    """Download `name` from CORDIS if missing and check its SHA-256.

    A mismatch only warns: CORDIS republishes its exports, so a fresh download
    may legitimately differ from the file the figures were produced with.
    """
    path = Path(raw_dir) / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(".part")  # an interrupted download must not pass for the real file
        urlretrieve(BASE_URL + name, partial)
        partial.rename(path)
    expected = {}
    for line in Path(sums_file).read_text().splitlines():
        digest, file_name = line.split()
        expected[file_name] = digest
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected.get(name) != actual:
        warnings.warn(
            f"{name}: SHA-256 {actual[:12]}... differs from {Path(sums_file).name}; "
            "CORDIS may have republished the file, figures can differ from the documented run."
        )
    return path


def read_cordis_csv(source):
    """Read a CORDIS CSV from a path or binary file object.

    Returns (dataframe, number_of_rows_excluded). Money columns come back as
    floats; rows the parser cannot split into the expected columns are dropped.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", pd.errors.ParserWarning)
        df = pd.read_csv(source, sep=";", quotechar='"', decimal=",", encoding="utf-8", on_bad_lines="warn")
    excluded = sum(str(w.message).count("Skipping line") for w in caught)
    return df, excluded


def read_from_zip(zip_path, member):
    """Read one CSV member straight from a CORDIS zip, without extracting it."""
    with zipfile.ZipFile(zip_path) as zf, zf.open(member) as f:
        return read_cordis_csv(f)


def matches_terms(df, terms, fields):
    """Flag rows where any of `terms` appears in any of `fields`, ignoring case.

    The rule is deliberately a plain list of words so that a non-technical
    reader can read it and challenge it. Returns a boolean Series.
    """
    text = df[list(fields)].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    return text.apply(lambda s: any(term.lower() in s for term in terms))


def draw_sample(df, strata, seed):
    """Draw a stratified sample; strata are disjoint and taken in the order given.

    `strata` is a list of (name, mask, n, sort_by): `n` rows from the rows
    that match `mask` and were not drawn by an earlier stratum, the `n`
    largest by `sort_by` if given, else at random with `seed`. Rows are
    sorted by id first, so the draw does not depend on the file's row order.
    """
    remaining = df.sort_values("id")
    drawn = []
    for name, mask, n, sort_by in strata:
        candidates = remaining[mask.loc[remaining.index]]
        if len(candidates) < n:
            raise ValueError(f"stratum {name!r}: {len(candidates)} candidates, {n} requested")
        picked = candidates.nlargest(n, sort_by) if sort_by else candidates.sample(n, random_state=seed)
        remaining = remaining.drop(picked.index)
        drawn.append(picked.assign(stratum=name))
    return pd.concat(drawn, ignore_index=True)


LABELS = {"central", "contributes", "none", "unsure", ""}
POSITIVE = {"central", "contributes"}


def agrees(label, predicted):
    """Row by row: does a yes/no prediction agree with the hand label?

    True or False where a label exists; None where the label is blank or
    `unsure`, so those rows can be counted apart rather than as errors.
    """
    label = label.fillna("").astype(str).str.strip().str.lower()
    unknown = sorted(set(label[~label.isin(LABELS)]))
    if unknown:
        raise ValueError(f"unknown label(s) {unknown}; use one of {sorted(LABELS - {''})}")
    predicted = predicted.astype(bool)
    out = (label.isin(POSITIVE) & predicted) | ((label == "none") & ~predicted)
    return out.astype(object).where(label.isin(POSITIVE | {"none"}), None)


def agreement(labelled):
    """Count, per stratum and in total, where the rule and the hand labels agree.

    `labelled` has columns `stratum`, `label` (one of `LABELS`, empty when not
    annotated yet) and `rule` (what the keyword rule says). `central` and
    `contributes` agree with rule=True, `none` with rule=False; `unsure` is
    counted apart. Counts only: twenty labels do not support a percentage.
    """
    label = labelled["label"].fillna("").astype(str).str.strip().str.lower()
    ok = agrees(label, labelled["rule"])
    rows = labelled.assign(
        label=label,
        labelled=label != "",
        unsure=label == "unsure",
        agree=ok.eq(True),
        disagree=ok.eq(False),
    )
    counts = rows.groupby("stratum").agg(
        projects=("label", "size"),
        labelled=("labelled", "sum"),
        agree=("agree", "sum"),
        disagree=("disagree", "sum"),
        unsure=("unsure", "sum"),
    )
    counts.loc["total"] = counts.sum()
    return counts.astype(int)


def write_once(df, path):
    """Write `df` to `path` as CSV unless the file exists: hand-filled answers are never overwritten."""
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
    return path


QUESTION = (
    "You read one EU-funded research project. Answer on two lines. Line 1, exactly one word: "
    "'central' if battery technology is the central object of the project, "
    "'contributes' if the project contributes to the battery value chain (recycling, storage, materials) "
    "without batteries being its object, 'none' if batteries are only mentioned in passing or in another sense, "
    "'unsure' if you cannot tell. Line 2: the one sentence of the objective you relied on, quoted verbatim."
)


def parse_label(answer):
    """Reduce the first line of a model's answer to one of the four labels; anything else is `unsure`."""
    first_line = answer.strip().split("\n", 1)[0].lower()
    for word in first_line.split():
        if word.strip(string.punctuation) in LABELS - {""}:
            return word.strip(string.punctuation)
    return "unsure"


def evidence(answer):
    """The sentence the model says it relied on: everything after the first line, or empty."""
    parts = answer.strip().split("\n", 1)
    return parts[1].strip() if len(parts) == 2 else ""


def ask_model(title, objective, api_key, base_url, model):
    """One short call to an OpenAI-compatible chat endpoint; returns the raw answer text.

    Kept to the standard library on purpose: no SDK, no new dependency, and the
    request is readable in full. In the unit, the same call would go to an
    approved tool, never to a public one with internal data.
    """
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": 120,
        "messages": [{"role": "system", "content": QUESTION}, {"role": "user", "content": f"Title: {title}\n\nObjective: {objective}"}],
    }
    request = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    for wait in (5, 30, 60, None):  # a free tier allows a few calls a minute: wait and retry when told so
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)["choices"][0]["message"]["content"]
        except HTTPError as error:
            if error.code != 429 or wait is None:
                raise
            time.sleep(wait)
