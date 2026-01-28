# CharacterTextSplitter Algorithm Description

## Algorithm Overview

The `CharacterTextSplitter` splits text into chunks with a maximum size of `chunk_size` characters, preferring word boundaries (spaces) when possible, and supporting overlap between chunks.

## Step-by-Step Algorithm

```python
def split_text(self, text: str) -> list[str]:
    chunks = []
    i = 0  # Current position in text
    
    while i < text_len:
        # Step 1: Calculate potential end position
        end = min(i + chunk_size, text_len)
        
        # Step 2: Try to find word boundary (if not at end of text)
        if end < text_len and separator exists:
            chunk_text = text[i:end]
            last_sep = chunk_text.rfind(separator)  # Find last space
            
            if last_sep > 0:
                # Move end to word boundary
                end = i + last_sep + len(separator)
        
        # Step 3: Extract chunk
        chunk = text[i:end]
        chunks.append(chunk)
        
        # Step 4: Move to next position (with overlap)
        if overlap > 0 and end < text_len:
            i = end - overlap  # Back up for overlap
        else:
            i = end  # No overlap, start after this chunk
```

## When Small Chunks (< 100 chars) Occur

### 1. **End of Text**
The most common reason: when the remaining text is shorter than `chunk_size`.

**Example:**
```
Text length: 1200 characters
Chunk 1: positions 0-512 (512 chars)
Chunk 2: positions 462-974 (512 chars, with 50 overlap)
Chunk 3: positions 924-1200 (276 chars) ← Small chunk at end
```

### 2. **Overlap Near End of Text**
When overlap causes the next chunk to start near the end of the text.

**Example:**
```
Text length: 1000 characters
Chunk 1: positions 0-512 (512 chars)
Chunk 2: positions 462-974 (512 chars, with 50 overlap)
Chunk 3: positions 924-1000 (76 chars) ← Small chunk due to overlap
```

### 3. **Word Boundary Adjustment Near End**
When a word boundary is found very close to the end of text, creating a small final chunk.

**Example:**
```
Text: "...very long word that ends at position 950"
i = 500, end = 1000 (would be 512 chars)
But last separator found at position 945
Adjusted end = 945 + 1 = 946
Chunk: positions 500-946 (446 chars)
Next: i = 946 - 50 = 896
Final chunk: positions 896-950 (54 chars) ← Small chunk
```

### 4. **No Separator Found**
If no separator is found in the chunk (very long word or special text), and we're near the end, we might get a small chunk.

**Example:**
```
Text: "...verylongwordwithoutspaces1234567890"
If we're at position 900 and text ends at 950:
- No separator found in chunk[900:1412] (would exceed text)
- end = 950 (end of text)
- Chunk: positions 900-950 (50 chars) ← Small chunk
```

## Why This Is Acceptable

Small chunks are **expected and acceptable** because:

1. **Text boundaries**: Real text doesn't always divide evenly into 512-character chunks
2. **Word integrity**: We prefer splitting at word boundaries, which may create smaller chunks near the end
3. **Overlap requirement**: Overlap can cause the final chunk to be smaller
4. **Strict limit**: The important guarantee is that **no chunk exceeds 512 characters**, not that all chunks are exactly 512

## Statistics Interpretation

From your output:
```
Chunk lengths: min=307, max=512, avg=495.4
✓ All chunks are ≤ 512 characters
```

This shows:
- **Min=307**: The smallest chunk is 307 characters (likely the final chunk or one near the end)
- **Max=512**: Some chunks hit the maximum (good - we're using the space efficiently)
- **Avg=495.4**: Average is close to 512, meaning most chunks are near the target size
- **All ≤ 512**: ✅ The critical guarantee is met

## Visual Example

Let's trace through an example with `chunk_size=512` and `chunk_overlap=50`:

```
Text: "This is a very long document..." (total: 1200 characters)

Iteration 1:
  i = 0
  end = min(0 + 512, 1200) = 512
  Find last space in text[0:512] → found at position 480
  Adjusted end = 480 + 1 = 481
  Chunk 1: text[0:481] = 481 characters
  Next i = 481 - 50 = 431 (overlap)

Iteration 2:
  i = 431
  end = min(431 + 512, 1200) = 943
  Find last space in text[431:943] → found at position 920
  Adjusted end = 920 + 1 = 921
  Chunk 2: text[431:921] = 490 characters
  Next i = 921 - 50 = 871 (overlap)

Iteration 3:
  i = 871
  end = min(871 + 512, 1200) = 1200 (end of text!)
  No word boundary search (at end of text)
  Chunk 3: text[871:1200] = 329 characters ← Smaller chunk at end
  Next i = 1200 (done)

Result: 3 chunks [481, 490, 329 chars]
```

## Algorithm Guarantees

✅ **Guaranteed**: No chunk will exceed `chunk_size` (512 characters)  
✅ **Guaranteed**: Chunks will prefer word boundaries when possible  
✅ **Guaranteed**: Overlap will be applied when specified  
⚠️ **Not guaranteed**: All chunks will be exactly `chunk_size`  
⚠️ **Not guaranteed**: Minimum chunk size (can be as small as 1 character if needed)

## Potential Improvements

If you want to avoid very small chunks, you could:

1. **Merge small final chunks**: If the last chunk is < 100 chars, merge it with the previous chunk
2. **Minimum chunk size**: Add a parameter to merge chunks smaller than a threshold
3. **Adjust overlap near end**: Reduce or eliminate overlap when near the end of text

However, the current behavior is **correct** - it ensures strict size limits while respecting word boundaries.
