# Index Building Quick Reference

## Command Examples

### Force Rebuild Word Index (Recommended for CharacterTextSplitter update)

```bash
cd /Users/erlebach/src/2026/grading_assessment/autograder
uv run python -m grading_pipeline.build_index --force-word
```

This will:
- Delete the existing word_index collection
- Rebuild with strict 512-character chunks using `CharacterTextSplitter`
- Keep the sentence_index unchanged

### Force Rebuild All Indexes

```bash
uv run python -m grading_pipeline.build_index --force
```

### Normal Incremental Build

```bash
uv run python -m grading_pipeline.build_index
```

This will:
- Skip unchanged sources
- Only index new or modified files
- Use lazy embedding loading (faster startup)

## Verification

After rebuilding, verify the chunks are correct:

```bash
uv run python -m grading_pipeline.test_chromadb_scores
```

Expected output:
```
Word Index (word_index):
  Total chunks in word_index: X
  Chunk lengths: min=..., max=512, avg=...
  ✓ All chunks are ≤ 512 characters
```

## Full Workflow

1. **Rebuild word index with new splitter:**
   ```bash
   uv run python -m grading_pipeline.build_index --force-word
   ```

2. **Verify chunks are correct:**
   ```bash
   uv run python -m grading_pipeline.test_chromadb_scores
   ```

3. **Run grading pipeline:**
   ```bash
   uv run python -m grading_pipeline.cli --question q01
   ```

## Troubleshooting

### "Collection not found" error

Delete the entire ChromaDB directory and rebuild:

```bash
rm -rf grading_pipeline/tmp/chroma_db/
uv run python -m grading_pipeline.build_index
```

### Slow embedding loading

The first time you build indexes, embeddings must be loaded. Use `--no-lazy` to load upfront:

```bash
uv run python -m grading_pipeline.build_index --no-lazy
```

### Custom config location

```bash
uv run python -m grading_pipeline.build_index \
    --config custom/path/sources.yaml \
    --output custom/output/dir
```

## Help

```bash
uv run python -m grading_pipeline.build_index --help
```
