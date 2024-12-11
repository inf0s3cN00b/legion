# flake8: noqa: E501
from typing import Dict, List
from src.agents.llm_base import LLMBase
from src.util.logging import Logger
import json
import html
from src.config.config import Config


class Chatbot(LLMBase):
    """Chatbot that maintains conversation history and can execute commands"""

    def __init__(self, max_history: int = 10):
        # Add specialized prompt for conversation and command handling
        self.config = Config()
        personality = self.config.get("llm.personality")

        # Combine personality with any other system instructions
        custom_prompt = (
            f"{personality}\n\n"
            "Additional instructions:\n"
            "1. When the user is asking for edits to their code, please output a simplified version "
            "of the code block that highlights the changes necessary.\n"
            "2. Do not lie or make up facts.\n"
            "3. If a user messages you in a foreign language, please respond in that language.\n"
            "4. Format your response in markdown.\n"
            "5. Always specify the language in code blocks.\n"
        )

        # Initialize LLMBase with all commands (pass None for command_names)
        super().__init__(custom_prompt=custom_prompt, command_names=None)

        self.logger = Logger("Chatbot")
        self.logger.info("Initialized with commands:", extra_data={"commands": list(self.commands.keys())})

        # Initialize conversation history
        self.max_history = max_history
        self.history: List[Dict[str, str]] = [{"role": "system", "content": self.system_prompt}]

    def _truncate_result(self, result: str, max_length: int = 4000) -> str:
        """Truncate a result string to a reasonable size"""
        if len(result) <= max_length:
            return result

        # For JSON strings, try to parse and truncate the content
        try:
            data = json.loads(result)
            if isinstance(data, dict):
                if "results" in data and isinstance(data["results"], list):
                    # Truncate results array
                    original_count = len(data["results"])
                    data["results"] = data["results"][:10]  # Keep only first 10 results
                    data["note"] = f"Results truncated to 10 of {original_count} total matches"
                return json.dumps(data, indent=2)  # Pretty print JSON
        except json.JSONDecodeError:
            pass

        # For plain text, truncate with ellipsis
        return result[:max_length] + "... (truncated)"

    def _format_response(self, text: str) -> str:
        """Format response text to be safe for Telegram"""
        # Escape any HTML-like characters
        text = html.escape(text)

        # Format code blocks and JSON
        if text.startswith("{") and text.endswith("}"):
            try:
                # Try to parse and pretty print JSON
                data = json.loads(text)
                return f"```\n{json.dumps(data, indent=2)}\n```"
            except json.JSONDecodeError:
                pass

        return text

    def _add_to_history(self, role: str, content: str) -> None:
        """Add a message to conversation history"""
        self.history.append({"role": role, "content": content})

        # Keep history within limits, but preserve system message
        if len(self.history) > self.max_history + 1:  # +1 for system message
            # Remove oldest messages but keep system message
            self.history = [self.history[0]] + self.history[-(self.max_history) :]

    async def process_message(self, message: str) -> str:
        """Process a user message and return a response"""
        try:
            # Add user message to history
            self._add_to_history("user", message)

            # First get AI's understanding of the request
            plan = await self.chat_completion(
                self.history
                + [
                    {
                        "role": "system",
                        "content": """Determine if this message requires executing any commands.
For casual conversation or greetings, just respond naturally.
Only suggest commands if the user is asking for specific information or actions.

IMPORTANT: You can only execute ONE command at a time. If you need multiple queries, execute the most relevant one first and wait for the result.

Database schema:
- projects table: Contains project information (id, name, project_type, etc.)
  keywords field is a JSON array of strings
- assets table: Contains assets (id, asset_type, source_url, etc.)
- project_assets table: Association table linking projects and assets (project_id, asset_id)
  project_assets.project_id references projects.id
  project_assets.asset_id references assets.id

If a command is needed, respond with exactly:
EXECUTE: command_name param=value

Example responses:
- For casual chat: Just respond normally
- For listing projects: EXECUTE: db_query query='{"from": "projects", "limit": 5}'
- For finding project assets: EXECUTE: db_query query='{"from": "assets", "join": {"table": "project_assets", "on": {"id": "asset_id"}}, "join": {"table": "projects", "on": {"project_id": "id"}}, "where": [{"field": "projects.name", "op": "ilike", "value": "%ProjectName%"}], "limit": 10}'
- For latest Solidity project: EXECUTE: db_query query='{"from": "projects", "where": [{"field": "keywords", "op": "@>", "value": ["Solidity"]}], "order_by": [{"field": "created_at", "direction": "desc"}], "limit": 1}'

Note:
- When joining tables through an association table, you need to join through project_assets first, then to projects.
- To search in JSON arrays like keywords, use the "@>" operator with an array value: {"op": "@>", "value": ["Keyword"]}

Do not try to execute multiple commands or modify queries based on previous results. Execute one command and wait for the response.
Do not use HTML formatting in your responses.""",
                    }
                ]
            )

            # For casual conversation, add response to history and return
            if "EXECUTE:" not in plan:
                formatted_response = self._format_response(plan)
                self._add_to_history("assistant", formatted_response)
                return formatted_response

            # Extract and execute the command
            command_line = plan.split("EXECUTE:", 1)[1].strip()
            self.logger.info(f"Processing command: {command_line}")

            # Parse command and parameters
            parts = command_line.split(" ", 1)
            if len(parts) != 2:
                error_msg = f"Invalid command format: {command_line}"
                self.logger.error(error_msg)
                return self._format_response(error_msg)

            command = parts[0]
            params_str = parts[1].strip()

            try:
                # Execute the command - parameter parsing is now handled in LLMBase
                result = await self.execute_command(command, params_str)

                # Truncate large results
                result = self._truncate_result(str(result))

                # Get AI to format the result nicely
                summary_messages = self.history + [
                    {
                        "role": "system",
                        "content": "Format these command results in a clear and helpful way. Do not use HTML formatting.",
                    },
                    {"role": "user", "content": result},
                ]

                formatted_response = await self.chat_completion(summary_messages)
                formatted_response = self._format_response(formatted_response)
                self._add_to_history("assistant", formatted_response)
                return formatted_response

            except Exception as e:
                error_msg = f"Error executing command: {str(e)}"
                self.logger.error(error_msg)
                return self._format_response(error_msg)

        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            self.logger.error(error_msg)
            return self._format_response(error_msg)
