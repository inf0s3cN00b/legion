"""Action to start GitHub monitoring"""

from src.actions.base import BaseAction, ActionSpec
from src.jobs.github_monitor import GithubMonitorJob
from src.config.config import Config


class GithubMonitorAction(BaseAction):
    """Action to trigger GitHub repository synchronization"""

    spec = ActionSpec(
        name="github_monitor",
        description="Synchronize GitHub repositories",
        help_text="""Synchronize GitHub repositories.

Usage:
/github_monitor

This command will:
1. Check all GitHub repositories in scope
2. Fetch new commits and pull requests
3. Trigger analysis of changes
4. Send notifications for important updates

The job performs a single synchronization run and then completes.""",
        agent_hint="Use this command to synchronize GitHub repositories and analyze any new changes.",
        arguments=[],
    )

    async def execute(self, *args, **kwargs) -> str:
        """Execute the GitHub monitor action"""
        # Import JobManager here to avoid circular imports
        from src.jobs.manager import JobManager

        # Get GitHub token from config
        config = Config()
        github_token = config.get("github.api_token")
        if not github_token:
            return "Error: GitHub API token not configured. Please set LEGION_GITHUB_TOKEN in config."

        # Pass token to job
        job = GithubMonitorJob(github_token=github_token)
        job_manager = JobManager()
        job_id = await job_manager.submit_job(job)

        return f"Started GitHub repository synchronization (Job ID: {job_id})"
