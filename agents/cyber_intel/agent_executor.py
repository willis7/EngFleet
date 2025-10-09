import logging

from typing import TYPE_CHECKING

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    FilePart,
    FileWithBytes,
    FileWithUri,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from google.adk import Runner
from google.genai import types


if TYPE_CHECKING:
    from google.adk.sessions.session import Session


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Constants
DEFAULT_USER_ID = "self"


class CyberIntelAgentExecutor(AgentExecutor):
    def __init__(self, runner: Runner, card: AgentCard):
        self.runner = runner
        self._card = card
        # Track active sessions for potential cancellation
        self._active_sessions: set[str] = set()

    async def _process_request(
        self,
        new_message: types.Content,
        session_id: str,
        task_updater: TaskUpdater,
    ) -> None:
        session_obj = await self._upsert_session(session_id)
        # Update session_id with the ID from the resolved session object.
        # (it may be the same as the one passed in if it already exists)
        session_id = session_obj.id

        # Track this session as active
        self._active_sessions.add(session_id)

        try:
            async for event in self.runner.run_async(
                session_id=session_id,
                user_id=DEFAULT_USER_ID,
                new_message=new_message,
            ):
                if event.is_final_response():
                    parts = [
                        convert_genai_part_to_a2a(part)
                        for part in event.content.parts
                        if (part.text or part.file_data or part.inline_data)
                    ]
                    logger.debug("Yielding final response: %s", parts)
                    await task_updater.add_artifact(parts)
                    await task_updater.update_status(TaskState.completed, final=True)
                    break
                if not event.get_function_calls():
                    logger.debug("Yielding update response")
                    await task_updater.update_status(
                        TaskState.working,
                        message=task_updater.new_agent_message(
                            [
                                convert_genai_part_to_a2a(part)
                                for part in event.content.parts
                                if (part.text)
                            ],
                        ),
                    )
                else:
                    logger.debug("Skipping event")
        finally:
            # Remove from active sessions when done
            self._active_sessions.discard(session_id)

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        # Run the agent until either complete or the task is suspended.
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        # Immediately notify that the task is submitted.
        if not context.current_task:
            await updater.update_status(TaskState.submitted)
        await updater.update_status(TaskState.working)
        await self._process_request(
            types.UserContent(
                parts=[
                    convert_a2a_part_to_genai(part) for part in context.message.parts
                ],
            ),
            context.context_id,
            updater,
        )
        logger.debug("[CyberIntelAgentExecutor] execute exiting")

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        """Cancel the execution for the given context.

        Currently logs the cancellation attempt as the underlying ADK runner
        doesn't support direct cancellation of ongoing tasks.
        """
        session_id = context.context_id
        if session_id in self._active_sessions:
            logger.info(
                f"Cancellation requested for active cyber intel session: {session_id}"
            )
            # TODO: Implement proper cancellation when ADK supports it
            self._active_sessions.discard(session_id)
        else:
            logger.debug(
                f"Cancellation requested for inactive cyber intel session: {session_id}"
            )

        raise ServerError(error=UnsupportedOperationError())

    async def _upsert_session(self, session_id: str) -> "Session":
        """Retrieves a session if it exists, otherwise creates a new one.

        Ensures that async session service methods are properly awaited.
        """
        session = await self.runner.session_service.get_session(
            app_name=self.runner.app_name,
            user_id=DEFAULT_USER_ID,
            session_id=session_id,
        )
        if session is None:
            session = await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id=DEFAULT_USER_ID,
                session_id=session_id,
            )
        return session


def convert_a2a_part_to_genai(part: Part) -> types.Part:
    """Convert a single A2A Part type into a Google Gen AI Part type.

    This function transforms message parts from the Agent-to-Agent (A2A) protocol
    format into the format expected by Google's Generative AI API. This conversion
    is necessary when sending messages from the A2A framework to the underlying
    LLM for processing.

    Supported conversions:
    - TextPart: Converts plain text content into a Gen AI text part
    - FilePart with FileWithBytes: Converts file data with inline bytes into
      a Gen AI Blob with inline_data
    - FilePart with FileWithUri: Converts file references by URI into Gen AI
      FileData with file_uri

    Args:
        part: The A2A Part object to convert. This is typically extracted from
              a message in the A2A protocol format.

    Returns:
        types.Part: A Google Gen AI Part object that can be included in content
                    sent to the Gen AI API.

    Raises:
        ValueError: If the part type is not one of the supported types (TextPart,
                    FilePart with FileWithBytes, or FilePart with FileWithUri).

    """
    part = part.root
    if isinstance(part, TextPart):
        return types.Part(text=part.text)
    if isinstance(part, FilePart):
        if isinstance(part.file, FileWithBytes):
            return types.Part(
                inline_data=types.Blob(
                    data=part.file.bytes,
                    mime_type=part.file.mime_type or "application/octet-stream",
                )
            )
        elif isinstance(part.file, FileWithUri):
            return types.Part(file_data=types.FileData(file_uri=part.file.uri))
    raise ValueError(f"Unsupported part type: {type(part)}")


def convert_genai_part_to_a2a(part: types.Part) -> Part:
    """Convert a single Google Gen AI Part type into an A2A Part type.

    Args:
        part: The Google Gen AI Part to convert

    Returns:
        The equivalent A2A Part

    Raises:
        ValueError: If the part type is not supported
    """
    if part.text:
        return TextPart(text=part.text)
    if part.inline_data:
        return Part(
            root=FilePart(
                file=FileWithBytes(
                    bytes=part.inline_data.data,
                    mime_type=part.inline_data.mime_type,
                )
            )
        )
    raise ValueError(f"Unsupported part type: {part}")
