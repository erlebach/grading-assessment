# Commands with quarto notebooks

## To render as HTML:
```text
  quarto render notebooks/grade_assignment_v2.qmd --to html
```

## To convert to Jupyter notebook:
```text
  quarto convert notebooks/grade_assignment_v2.qmd
```
produces grade_assignment_v2.ipynb

## To execute and render in one step:
```text
  quarto render notebooks/grade_assignment_v2.qmd --execute
```
(requires execute: eval: true in the YAML header, or pass --execute flag)
