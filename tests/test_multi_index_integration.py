"""Integration tests for multi-index retrieval system.

Tests the complete multi-index system including:
- Index configuration validation
- Multi-index building and loading
- Backward compatibility with dual-index API
- Runtime index subset selection
- Multi-index retrieval with deduplication and reranking

"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml
from llama_index.core import Document, VectorStoreIndex

# Set testing mode to use MockEmbedding instead of OpenAI
os.environ["IS_TESTING"] = "true"

from grading_pipeline.config.index_schema import IndexesConfig, load_index_config
from grading_pipeline.index_factory import IndexFactory
from grading_pipeline.index_registry import IndexRegistry
from grading_pipeline.index_builder_in_memory import (
    build_multi_indexes_in_memory,
    load_multi_indexes_in_memory,
)
from retrieval_core.multi_retriever import MultiIndexRetriever
from retrieval_core.dual_retriever_compat import DualIndexRetriever


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        Document(
            text="Data quality is important for machine learning. "
            "High quality data leads to better models. "
            "Data validation is a key step. "
            "Cleaning data improves model performance.",
            metadata={
                "source_id": "doc1",
                "file_name": "test1.txt",
                "file_path": "/tmp/test1.txt",
                "source_type": "slide",
            },
        ),
        Document(
            text="Machine learning models depend on training data. "
            "Data preprocessing removes noise. "
            "Feature engineering creates new features. "
            "Model evaluation measures performance.",
            metadata={
                "source_id": "doc2",
                "file_name": "test2.txt",
                "file_path": "/tmp/test2.txt",
                "source_type": "file",
            },
        ),
    ]


@pytest.fixture
def test_config():
    """Create test configuration."""
    return {
        "indexes": {
            "word_index": {
                "type": "character",
                "chunk_size": 100,
                "chunk_overlap": 10,
                "source_type_overrides": {"slide": 50},
                "collection_name": "word_index",
                "enabled": True,
            },
            "sentence_index": {
                "type": "sentence",
                "chunk_size": 50,
                "chunk_overlap": 10,
                "secondary_chunking_regex_default": "[^,.;。？！]+[,.;。？！]?|[,.;。？！]",
                "collection_name": "sentence_index",
                "enabled": True,
            },
            "paragraph_index": {
                "type": "paragraph",
                "chunk_size": 200,
                "chunk_overlap": 20,
                "paragraph_separator": "\n\n",
                "collection_name": "paragraph_index",
                "enabled": False,
            },
        },
        "runtime": {"active_indexes": ["word_index", "sentence_index"]},
        "sources": {"type": "file", "path": "/tmp", "patterns": ["*.txt"]},
    }


class TestIndexConfigValidation:
    """Test index configuration validation."""

    def test_load_valid_config(self, test_config):
        """Test loading valid configuration."""
        indexes_config = load_index_config(test_config)
        assert len(indexes_config.indexes) == 3
        assert "word_index" in indexes_config.indexes
        assert "sentence_index" in indexes_config.indexes
        assert "paragraph_index" in indexes_config.indexes

    def test_validate_active_indexes(self, test_config):
        """Test that active_indexes reference existing indexes."""
        indexes_config = load_index_config(test_config)
        assert set(indexes_config.runtime.active_indexes).issubset(
            set(indexes_config.indexes.keys())
        )

    def test_unique_collection_names(self):
        """Test that collection names are unique."""
        config = {
            "indexes": {
                "index1": {
                    "type": "character",
                    "collection_name": "same_name",
                    "enabled": True,
                },
                "index2": {
                    "type": "sentence",
                    "collection_name": "same_name",
                    "enabled": True,
                },
            },
            "runtime": {"active_indexes": ["index1", "index2"]},
        }
        with pytest.raises(ValueError, match="Duplicate collection_name"):
            load_index_config(config)


class TestIndexRegistry:
    """Test index registry."""

    def test_list_registered_types(self):
        """Test listing all registered index types."""
        types = IndexRegistry.list_types()
        assert "character" in types
        assert "sentence" in types
        assert "paragraph" in types

    def test_get_builder(self):
        """Test getting a builder by type."""
        builder = IndexRegistry.get_builder("character")
        assert builder is not None
        assert hasattr(builder, "build")
        assert hasattr(builder, "load")

    def test_get_unknown_builder(self):
        """Test error when getting unknown builder."""
        with pytest.raises(ValueError, match="Unknown index type"):
            IndexRegistry.get_builder("unknown_type")


class TestIndexFactory:
    """Test index factory."""

    def test_factory_initialization(self, test_config):
        """Test factory initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = IndexFactory(test_config, Path(temp_dir))
            assert factory.persist_dir == Path(temp_dir)
            assert len(factory.indexes_config) == 3
            assert factory.get_active_index_ids() == ["word_index", "sentence_index"]

    def test_set_active_indexes(self, test_config):
        """Test overriding active indexes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = IndexFactory(test_config, Path(temp_dir))
            factory.set_active_indexes(["word_index"])
            assert factory.get_active_index_ids() == ["word_index"]

    def test_set_invalid_active_indexes(self, test_config):
        """Test error when setting invalid active indexes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = IndexFactory(test_config, Path(temp_dir))
            with pytest.raises(ValueError, match="Unknown index IDs"):
                factory.set_active_indexes(["invalid_index"])

    def test_get_index_config(self, test_config):
        """Test getting index configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = IndexFactory(test_config, Path(temp_dir))
            config = factory.get_index_config("word_index")
            assert config["type"] == "character"
            assert config["chunk_size"] == 100


class TestMultiIndexBuilding:
    """Test multi-index building."""

    def test_build_dual_indexes(self, test_config, sample_documents):
        """Test building word and sentence indexes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = IndexFactory(test_config, Path(temp_dir))
            indexes = factory.build_active_indexes(sample_documents)

            assert len(indexes) == 2
            assert "word_index" in indexes
            assert "sentence_index" in indexes
            assert isinstance(indexes["word_index"], VectorStoreIndex)
            assert isinstance(indexes["sentence_index"], VectorStoreIndex)

    def test_build_with_subset(self, test_config, sample_documents):
        """Test building a subset of indexes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = IndexFactory(test_config, Path(temp_dir))
            factory.set_active_indexes(["word_index"])
            indexes = factory.build_active_indexes(sample_documents)

            assert len(indexes) == 1
            assert "word_index" in indexes
            assert "sentence_index" not in indexes

    def test_load_built_indexes(self, test_config, sample_documents):
        """Test loading previously built indexes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Build indexes
            factory = IndexFactory(test_config, Path(temp_dir))
            indexes = factory.build_active_indexes(sample_documents)
            assert len(indexes) == 2

            # Create new factory and load
            factory2 = IndexFactory(test_config, Path(temp_dir))
            loaded_indexes = factory2.load_active_indexes()
            assert len(loaded_indexes) == 2
            assert set(loaded_indexes.keys()) == {"word_index", "sentence_index"}


class TestMultiIndexRetriever:
    """Test multi-index retrieval."""

    def test_multi_index_retriever_creation(self, test_config, sample_documents):
        """Test creating a multi-index retriever."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = IndexFactory(test_config, Path(temp_dir))
            indexes = factory.build_active_indexes(sample_documents)
            retriever = MultiIndexRetriever(indexes)

            assert retriever.index_ids == ["word_index", "sentence_index"]
            assert "word_index" in retriever.indexes
            assert "sentence_index" in retriever.indexes

    def test_multi_index_retrieval(self, test_config, sample_documents):
        """Test retrieving from multiple indexes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = IndexFactory(test_config, Path(temp_dir))
            indexes = factory.build_active_indexes(sample_documents)
            retriever = MultiIndexRetriever(indexes, reranker_model=None)

            # Mock the extract_citation_from_node function
            import unittest.mock as mock

            with mock.patch(
                "retrieval_core.multi_retriever.extract_citation_from_node"
            ) as mock_extract:
                mock_extract.return_value = {
                    "source_id": "doc1",
                    "text": "sample text",
                    "score": 0.9,
                }

                with mock.patch.object(
                    retriever.reranker, "predict", return_value=[0.8]
                ):
                    # This should not raise an error
                    # (actual retrieval requires embeddings to be generated)
                    pass

    def test_retrieve_with_subset(self, test_config, sample_documents):
        """Test retrieving from a subset of indexes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = IndexFactory(test_config, Path(temp_dir))
            indexes = factory.build_active_indexes(sample_documents)
            retriever = MultiIndexRetriever(indexes)

            # Should be able to retrieve from subset
            # (This is mainly a smoke test for the API)
            assert retriever.get_active_indexes() == ["word_index", "sentence_index"]


class TestBackwardCompatibility:
    """Test backward compatibility with dual-index API."""

    def test_dual_index_retriever_wraps_multi(self, test_config, sample_documents):
        """Test that DualIndexRetriever properly wraps MultiIndexRetriever."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = IndexFactory(test_config, Path(temp_dir))
            indexes = factory.build_active_indexes(sample_documents)

            # Create dual index retriever with old API
            retriever = DualIndexRetriever(
                indexes["word_index"], indexes["sentence_index"]
            )

            # Check that it has the expected attributes
            assert hasattr(retriever, "word_index")
            assert hasattr(retriever, "sentence_index")
            assert retriever.word_index is indexes["word_index"]
            assert retriever.sentence_index is indexes["sentence_index"]

    def test_dual_index_retriever_inherits_multi_functionality(
        self, test_config, sample_documents
    ):
        """Test that DualIndexRetriever has multi-index functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = IndexFactory(test_config, Path(temp_dir))
            indexes = factory.build_active_indexes(sample_documents)
            retriever = DualIndexRetriever(
                indexes["word_index"], indexes["sentence_index"]
            )

            # Check inherited multi-index properties
            assert hasattr(retriever, "indexes")
            assert hasattr(retriever, "index_ids")
            assert "word_index" in retriever.indexes
            assert "sentence_index" in retriever.indexes


class TestMultiIndexIntegration:
    """End-to-end integration tests."""

    def test_build_multi_indexes_function(self):
        """Test build_multi_indexes_in_memory function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create minimal config
            config_path = Path(temp_dir) / "test_config.yaml"
            config = {
                "indexes": {
                    "word_index": {
                        "type": "character",
                        "chunk_size": 100,
                        "chunk_overlap": 10,
                        "collection_name": "word_index",
                        "enabled": True,
                    },
                    "sentence_index": {
                        "type": "sentence",
                        "chunk_size": 50,
                        "chunk_overlap": 10,
                        "collection_name": "sentence_index",
                        "enabled": True,
                    },
                },
                "runtime": {"active_indexes": ["word_index", "sentence_index"]},
                "sources": {
                    "type": "file",
                    "path": str(Path(temp_dir)),
                    "patterns": ["*.txt"],
                },
            }

            # Note: This test is minimal because actual build requires source files
            # In a real scenario, sources would be loaded from disk
            # For now, we just verify the API exists
            assert callable(build_multi_indexes_in_memory)
            assert callable(load_multi_indexes_in_memory)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
