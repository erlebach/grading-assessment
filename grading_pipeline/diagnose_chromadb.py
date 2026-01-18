#!/usr/bin/env python3
"""Diagnostic script to check ChromaDB index status.

This script checks:
1. What collections exist
2. How many documents/chunks are in each collection
3. Whether embeddings are actually stored
4. Collection metadata

Usage:
    uv run python -m grading_pipeline.diagnose_chromadb
"""

from pathlib import Path

try:
    import chromadb
except ImportError:
    print("Error: chromadb not installed")
    exit(1)


def main() -> None:
    """Diagnose ChromaDB index status."""
    persist_dir = Path(__file__).parent / "tmp" / "chroma_db"
    
    print("=" * 80)
    print("ChromaDB Index Diagnostic")
    print("=" * 80)
    print(f"Database location: {persist_dir}")
    print()
    
    if not persist_dir.exists():
        print("❌ ChromaDB directory does not exist!")
        print(f"   Expected: {persist_dir}")
        print()
        print("Run: uv run python -m grading_pipeline.build_index")
        return
    
    # Check what files exist
    print("Files in ChromaDB directory:")
    files = list(persist_dir.iterdir())
    if not files:
        print("  (empty directory)")
    else:
        for f in sorted(files):
            if f.is_file():
                size = f.stat().st_size
                print(f"  📄 {f.name} ({size:,} bytes)")
            elif f.is_dir():
                print(f"  📁 {f.name}/")
    print()
    
    try:
        chroma_client = chromadb.PersistentClient(path=str(persist_dir))
        collections = chroma_client.list_collections()
        
        print(f"Collections found: {len(collections)}")
        print()
        
        if not collections:
            print("❌ No collections found in ChromaDB!")
            print()
            print("This means:")
            print("  1. Indexes were never created, OR")
            print("  2. Collections were created but not populated, OR")
            print("  3. Collections were deleted")
            print()
            print("Run: uv run python -m grading_pipeline.build_index --force")
            return
        
        for collection in collections:
            print(f"Collection: {collection.name}")
            print(f"  Metadata: {collection.metadata}")
            
            try:
                count = collection.count()
                print(f"  Document count: {count}")
                
                if count == 0:
                    print("  ⚠ WARNING: Collection exists but is empty!")
                    print("     This means embeddings were not stored.")
                else:
                    # Get a sample document to verify it has embeddings
                    sample = collection.get(limit=1, include=["embeddings", "documents", "metadatas"])
                    if sample.get("embeddings"):
                        emb_dim = len(sample["embeddings"][0]) if sample["embeddings"] else 0
                        print(f"  ✓ Embeddings present (dimension: {emb_dim})")
                    else:
                        print("  ⚠ WARNING: No embeddings found in sample document!")
                    
                    if sample.get("documents"):
                        doc_len = len(sample["documents"][0]) if sample["documents"] else 0
                        print(f"  ✓ Documents present (sample length: {doc_len} chars)")
                    
                    if sample.get("metadatas"):
                        print(f"  ✓ Metadata present: {list(sample['metadatas'][0].keys())}")
                
            except Exception as e:
                print(f"  ❌ Error reading collection: {e}")
            
            print()
        
        print("=" * 80)
        print("Summary")
        print("=" * 80)
        
        total_chunks = sum(c.count() for c in collections)
        if total_chunks == 0:
            print("❌ No chunks found in any collection!")
            print()
            print("Possible causes:")
            print("  1. Embedding model was not set before indexing")
            print("  2. Documents were empty or had no text")
            print("  3. Indexing failed silently")
            print()
            print("To fix:")
            print("  1. Check that embedding model is configured in ~/.env")
            print("  2. Verify documents have text content")
            print("  3. Rebuild indexes: uv run python -m grading_pipeline.build_index --force")
        else:
            print(f"✓ Total chunks across all collections: {total_chunks}")
            print("✓ Indexes appear to be populated correctly")
        
    except Exception as e:
        print(f"❌ Error accessing ChromaDB: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
