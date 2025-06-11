"""Application pipelines for orchestrating complex operations."""

from .clone_pipeline import CloneAllPipeline
from .pull_pipeline import PullAllPipeline

__all__ = ["CloneAllPipeline", "PullAllPipeline"]