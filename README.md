# Horizon Europe portfolio: batteries

![tests](https://github.com/ggustin93/horizon-europe-portfolio-batteries/actions/workflows/ci.yml/badge.svg)

A short, reproducible look at what Horizon Europe has funded on batteries, built on the public CORDIS data. It starts from a deliberately vague request ("We need to know what we've funded on batteries and whether it's working. Can you build us something with AI?") and shows how a business analyst turns it into a small, checkable data exploration before any tool is chosen.

This repository is the practical annex to a written note submitted for the same assignment. Nothing needs to run to follow the reasoning: GitHub renders [the notebook](horizon_batteries.ipynb) with its outputs, and an HTML export is attached to the e-mail. The notebook is the working environment; GitHub and VS Code are there to share it and open it.

## How I approached the assignment

I started from the request as the user phrased it and separated its three questions (what was funded, what came out, where the gaps are) from the solution it asked for. I then checked the data before anything else: which files exist, which rows cannot be read, which taxonomy labels are missing. After counting, I compared a simple rule with 20 projects I read by hand, so that any later AI step has a baseline to beat. The repository is small: one notebook, one module and its tests.

## Where each assignment item is addressed

| Assignment item | Note | Here |
|---|---|---|
| User needs analysis | § 1 | Notebook, introduction (before section 1) and section 8 (what the unit should decide next) |
| Conceptual framework | § 2 | Notebook, sections 4 to 6 (scope, what was funded, what came out); the instrument chart of section 5 is Appendix B of the note |
| AI and data approach | § 3 | Notebook, sections 2, 3 and 7 (quality check, FAIR check, 20 projects read by hand, optional model step) |
| Practical use of tools | § 4 | This repository: notebook, module, tests, continuous integration, this README |
| Implementation considerations | § 5 | Notebook, section 8; "Scaling up" below |
| Practical annex | § 4, first paragraph | This repository, and the HTML export of the notebook attached to the e-mail |
| Process diagram (Appendix A) | Appendix A | Notebook, section 7 (the labelling and check steps of the diagram) |

## Contents

| Path | What it is |
|---|---|
| `horizon_batteries.ipynb` | The notebook: the request, the data and its reuse terms, a quality check, a FAIR check (findable, accessible, interoperable, reusable), two definitions of the battery scope and their grey zone, what was funded (by year, instrument, programme part, participants, sub-themes), what came out so far (publications, deliverables, reports), a consistency check of the keyword rule on 20 projects read by hand, and what the unit should decide next. Readable as-is on GitHub. |
| `src/cordis.py` | A small module the notebook calls: download the CORDIS files and check they are the ones the figures were made with, read them, flag projects by keyword, draw the 20-project sample, count where the rule, the hand labels and the optional model agree. |
| `tests/` | Unit tests for the module, on a tiny sample file, no network needed. |
| `data/annotation/` | The 20 projects labelled by hand (`sample.csv`: id, acronym, title, objective and a `label` column filled with `central`, `contributes`, `none` or `unsure`) and their strata, kept apart so that labelling is blind (`strata.csv`). Written once by the notebook, never overwritten. `model_answers.csv` is the log of the one model run kept in the notebook. |
| `data/SHA256SUMS` | Fingerprints of the CORDIS archives the figures were produced with (the archives themselves are downloaded on first run, not committed). |
| `.github/workflows/ci.yml` | Runs the tests and executes the notebook on every change. |

## Run it

This section is for readers who want to reproduce the figures; skip it to just read. Requires Python 3.12. The code is simple and optional: it reads files, counts and compares.

```bash
git clone https://github.com/ggustin93/horizon-europe-portfolio-batteries.git
cd horizon-europe-portfolio-batteries
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                                   # unit tests, a second or two
pytest --nbmake horizon_batteries.ipynb  # executes the notebook end to end (downloads ~60 MB on first run)
```

The last step of the notebook, a small language-model prototype, runs only if `LLM_API_KEY` is set in the environment (`LLM_BASE_URL` and `LLM_MODEL` select any OpenAI-compatible provider). Without a key it prints a message and is skipped, as in the continuous integration. The run kept in the notebook used `LLM_MODEL=ministral-8b-latest`.

To export the notebook, with the outputs it already holds, as a standalone HTML page (the file attached to the e-mail):

```bash
jupyter nbconvert --to html horizon_batteries.ipynb
```

## Open it in VS Code

Open the folder in VS Code; it recommends the Python and Jupyter extensions. Select the `.venv` interpreter, open `horizon_batteries.ipynb` and run all cells.

## Scaling up

The same steps apply to the whole of Horizon Europe, then to the other centrally managed programmes: a new theme changes only the keyword rule and the 20 labels. Antimicrobial resistance, for instance, would span Horizon Europe, its Global Health EDCTP3 Joint Undertaking and EU4Health.

## AI use statement

The code, the formatting and the drafting of the note and of the text in this repository were assisted by Claude Code (Anthropic). The framing, the decisions, the 20 hand labels and the final wording are mine. Every figure except the single model run can be reproduced by running the notebook on the same CORDIS snapshot (`data/SHA256SUMS`).

## Data

CORDIS, EU research projects under Horizon Europe (2021-2027), © European Union. Reused under the Commission's reuse policy (Decision 2011/833/EU); CORDIS releases the dataset under the CC BY 4.0 licence. The files are used as published; the notebook states which files it reads and how many rows it excludes because they cannot be parsed. `data/annotation/sample.csv` reproduces the titles and objectives of 20 CORDIS projects (CC BY 4.0, https://creativecommons.org/licenses/by/4.0/); the `label` column is mine.

## Licence

The code is released under the European Union Public Licence, EUPL-1.2 (see `LICENSE`). The CORDIS data stays under CC BY 4.0.
