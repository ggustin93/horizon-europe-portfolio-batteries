# Horizon Europe portfolio: batteries

[![Read the report](https://img.shields.io/badge/Read%20the%20report-web%20page-1F3A93)](https://ggustin93.github.io/horizon-europe-portfolio-batteries/horizon_batteries.html)
[![tests](https://github.com/ggustin93/horizon-europe-portfolio-batteries/actions/workflows/ci.yml/badge.svg)](https://github.com/ggustin93/horizon-europe-portfolio-batteries/actions/workflows/ci.yml)

This repository takes a short look at what Horizon Europe has funded on batteries, using the public CORDIS data. It is the annex to a written note for a practical assignment: an exploration of what the public data can and cannot say, not an evaluation of the programme.

**[The report](https://ggustin93.github.io/horizon-europe-portfolio-batteries/horizon_batteries.html)** is the place to start: it is the notebook exported as a web page, with its code folded away. A reader with little time can keep to the summary at the top, the chart in section 5 and section 8, which lists what the policy unit should decide next. [The notebook](https://github.com/ggustin93/horizon-europe-portfolio-batteries/blob/main/horizon_batteries.ipynb) holds the same text and results together with the code, and nothing needs to be run to read either. The notebook is the working document; GitHub shares it and VS Code opens it.

## Where each assignment item is addressed

| Assignment item | In the note | In the annex |
|---|---|---|
| User needs analysis | § 1 | Notebook, the request (top) and section 8 |
| Conceptual framework | § 2 | Notebook, sections 4 to 6; the section 5 chart is Appendix B of the note |
| AI and data approach | § 3 | Notebook, sections 1 to 3 (data checks) and section 7 (20 projects read by hand, optional model step) |
| Practical use of tools | § 4 | This repository and the report |
| Implementation considerations | § 5 | Notebook, sections 7 and 8 |

## How I approached the task

The request came from a policy unit: *"We need to know what we've funded on batteries and whether it's working. Can you build us something with AI?"* I separated the three questions it asks or implies (what was funded, what came out, where the gaps are) from the solution it names. Before choosing any tool, I checked the data: which files exist, which rows cannot be read, which taxonomy labels are missing. I then counted the projects that a keyword rule flags, and checked that rule against 20 hard cases I labelled by hand. They can show a gross failure of the rule, but are too few, and too unbalanced, to measure the accuracy of the rule or of a model.

## AI use statement

Claude Code (Anthropic) helped with the code, the formatting and the drafting of the note and of this repository's text. The framing, the decisions, the 20 hand labels and the final wording are mine. The notebook's optional model step was run once, with Mistral AI's small language model `ministral-8b-latest`; its answers are logged in `data/annotation/model_answers.csv`.

## Contents

| Path | What it is |
|---|---|
| `horizon_batteries.ipynb` | The analysis, in 8 sections: data and reuse terms, quality check, FAIR check, scope, what was funded, what came out, 20 projects read by hand (and the optional model step), what the unit should decide next. |
| `horizon_batteries.html` | The report: the notebook exported as a web page, with the outputs it holds and the code folded. |
| `src/cordis.py` | The small module the notebook calls: it downloads and checks the CORDIS files, flags projects by keyword, draws the 20-project sample, asks the optional model and counts where the rule, the hand labels and the model agree. |
| `tests/` | Unit tests for the module, on a tiny sample file and small in-memory tables; no internet access needed. |
| `templates/report/` | The page template of the report: code and the list of the 20 model answers folded behind a toggle, a list of sections, print styles. |
| `data/annotation/` | The 20 hand-labelled projects (`sample.csv`) and the stratum each was drawn from (`strata.csv`, kept apart so that the labeller does not see it); neither is ever overwritten. `model_answers.csv` logs the model run shown in the notebook; a new run with an API key overwrites it. |
| `data/SHA256SUMS` | SHA-256 fingerprints of the CORDIS archives the figures were produced with (the archives themselves are downloaded on first run, not committed). |
| `.github/workflows/ci.yml` | Runs the tests and executes the notebook on every push and pull request, downloading about 60 MB from CORDIS each time. It checks that the code runs, not that the figures match. |

## Run it

This section is for readers who want to rerun the analysis. It needs Python 3.12. The code is simple and optional: it reads files, counts and compares.

```bash
git clone https://github.com/ggustin93/horizon-europe-portfolio-batteries.git
cd horizon-europe-portfolio-batteries
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                                   # unit tests, a second or two
pytest --nbmake horizon_batteries.ipynb  # executes the notebook end to end (downloads ~60 MB on first run)
```

The model step in section 7 runs only if `LLM_API_KEY` is set in the environment (`LLM_BASE_URL` and `LLM_MODEL` choose any OpenAI-compatible provider and model; the defaults are Mistral AI and `mistral-small-latest`). To repeat the run shown in the notebook, set `LLM_MODEL=ministral-8b-latest`. Running and saving the notebook replaces that output: section 7 then shows a "skipped" message without a key, or a new run with one, while its text still describes the original run. Any run with a key also overwrites `data/annotation/model_answers.csv`.

The command below rebuilds the report (`horizon_batteries.html`) from the outputs the notebook already holds, with the code folded behind a "Code" toggle:

```bash
jupyter nbconvert --to html --template report --TemplateExporter.extra_template_basedirs=templates horizon_batteries.ipynb
```

## Open it in VS Code

Open the repository folder in VS Code, which then suggests the Python and Jupyter extensions. Select the `.venv` interpreter and open `horizon_batteries.ipynb`.

## Data

CORDIS, EU research projects under Horizon Europe (2021-2027), © European Union: archives of early October 2026 (latest file dated 8 October), from [data.europa.eu](https://data.europa.eu/data/datasets/cordis-eu-research-projects-under-horizon-europe-2021-2027). CORDIS releases the dataset under the CC BY 4.0 licence, in line with the Commission's reuse policy (Decision 2011/833/EU). The files are not modified; the notebook excludes the rows it cannot read and reports how many.

Apart from the hand labels and the model answers, every figure is computed from the CORDIS archives whose SHA-256 fingerprints are recorded in `data/SHA256SUMS`. CORDIS replaces its archives without keeping old versions: on newer files the notebook warns and the figures may differ.

`data/annotation/sample.csv` reproduces the titles and objectives of 20 CORDIS projects, and `model_answers.csv` holds the passages the model quoted from them, abridged in places and not checked ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)). The selection and the `label` column are mine.

## Licence

The code is released under the European Union Public Licence, EUPL-1.2 (see `LICENSE`). The CORDIS data stays under CC BY 4.0. To credit this work, cite this repository and its author; credit the data to the European Union (CORDIS).
