"""
Pipeline orchestration for AI Content Studio Personal.

The orchestrator controls execution order. Agents do not call each other.
"""

from __future__ import annotations

from agents.director_agent import DirectorAgent
from agents.idea_agent import IdeaAgent
from models.project import Project


class PipelineOrchestrator:
    """Run the current agent pipeline in order."""

    def __init__(self) -> None:
        self.idea_agent = IdeaAgent()
        self.director_agent = DirectorAgent()

    def run(self, project: Project) -> Project:
        """Execute the configured pipeline for a project."""
        project = self.idea_agent.run(project)
        project = self.director_agent.run(project)
        return project
