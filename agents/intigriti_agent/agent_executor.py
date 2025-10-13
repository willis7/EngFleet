import logging
from typing import TYPE_CHECKING

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
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


class IntigritiAgentExecutor(AgentExecutor):
    """Executor for the Intigriti Agent that handles A2A protocol communication.

    This executor manages the lifecycle of agent requests, including session
    management, message conversion between A2A and Gen AI formats, and event
    streaming back to clients.
    """

    def __init__(self, runner: Runner, card: AgentCard):
        """Initialize the Intigriti Agent Executor.

        Args:
            runner: The ADK Runner instance that executes the agent
            card: The AgentCard containing agent metadata and capabilities
        """
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
        """Process a single request through the Intigriti agent.

        Args:
            new_message: The message content to send to the agent
            session_id: The session identifier for this conversation
            task_updater: Interface for updating task status and results
        """
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
                # Convert the event to A2A format and send to client
                if event.message:
                    parts = [
                        convert_genai_part_to_a2a(part) for part in event.message.parts
                    ]
                    await task_updater.update_status(
                        TaskState.working,
                        parts=parts,
                    )

                # Check if this is the final event
                if event.is_final:
                    await task_updater.update_status(
                        TaskState.completed,
                        final=True,
                    )
        except Exception as e:
            logger.error(f"Error processing Intigriti agent request: {e}")
            await task_updater.update_status(
                TaskState.failed,
                message=f"Failed to process request: {str(e)}",
                final=True,
            )
            raise
        finally:
            self._active_sessions.discard(session_id)

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        """Execute an agent request and stream results back via the event queue.

        Args:
            context: The request context containing session and message information
            event_queue: Queue for streaming events back to the client
        """
        logger.debug("[IntigritiAgentExecutor] execute called")

        session_id = context.context_id
        task_updater = TaskUpdater(event_queue, context)

        # Convert A2A message parts to Gen AI format
        new_message = types.Content(
            parts=[
                convert_a2a_part_to_genai(part) for part in context.input_request.parts
            ],
            role="user",
        )

        await self._process_request(new_message, session_id, task_updater)
        logger.debug("[IntigritiAgentExecutor] execute exiting")

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        """Cancel the execution for the given context.

        Currently logs the cancellation attempt as the underlying ADK runner
        doesn't support direct cancellation of ongoing tasks.

        Args:
            context: The request context to cancel
            event_queue: Event queue for sending cancellation status
        """
        session_id = context.context_id
        if session_id in self._active_sessions:
            logger.info(
                f"Cancellation requested for active Intigriti session: {session_id}"
            )
            # TODO: Implement proper cancellation when ADK supports it
            self._active_sessions.discard(session_id)
        else:
            logger.debug(
                f"Cancellation requested for inactive Intigriti session: {session_id}"
            )

        raise ServerError(error=UnsupportedOperationError())

    async def _upsert_session(self, session_id: str) -> "Session":
        """Retrieves a session if it exists, otherwise creates a new one.

        Ensures that async session service methods are properly awaited.

        Args:
            session_id: The identifier for the session

        Returns:
            The existing or newly created session object
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

    The Intigriti agent only supports text-based interactions for querying the
    Intigriti API, such as:
    - Listing bug bounty programs
    - Checking submission statuses
    - Retrieving vulnerability reports
    - Accessing reward information

    Args:
        part: The A2A Part object to convert. This is typically extracted from
              a message in the A2A protocol format. The part will be unwrapped
              from its root container before conversion.

    Returns:
        types.Part: A Google Gen AI Part object containing text content that
                    can be sent to the Gen AI API for processing by the agent.

    Raises:
        ValueError: If the part type is not TextPart. File inputs are not
                    supported by this agent.
    """
    part = part.root
    if isinstance(part, TextPart):
        return types.Part(text=part.text)
    raise ValueError(
        f"Unsupported part type: {type(part)}. "
        "Intigriti agent only supports text inputs."
    )


def convert_genai_part_to_a2a(part: types.Part) -> Part:
    """Convert a single Google Gen AI Part type into an A2A Part type.

    This function performs the reverse conversion of convert_a2a_part_to_genai,
    transforming text responses from Google's Generative AI API back into the
    A2A protocol format for transmission to clients.

    The Intigriti agent only returns text responses containing information
    retrieved from the Intigriti API.

    Args:
        part: The Google Gen AI Part to convert. This typically comes from
              the agent's response stream.

    Returns:
        Part: The equivalent A2A Part wrapped in a TextPart container.

    Raises:
        ValueError: If the part type is not text. The Intigriti agent only
                    returns text responses.
    """
    if part.text:
        return Part(root=TextPart(text=part.text))
    raise ValueError(
        f"Unsupported part type: {part}. Intigriti agent only returns text responses."
    )
