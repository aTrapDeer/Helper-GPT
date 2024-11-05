from AgentFunctions.screenHelp import AssistantScreenFnc
from AgentFunctions.webHelp import AssistantWebFnc
from AgentFunctions.locationHelp import AssistantLocationFnc
from livekit.agents import llm
import asyncio
import logging

logger = logging.getLogger(__name__)



class AgentFunctions(llm.FunctionContext):
    def __init__(self) -> None:
        super().__init__()
        self._lock = asyncio.Lock()
        self.web_assistant = AssistantWebFnc()
        self.screen_assistant = AssistantScreenFnc()
        self.location_assistant = AssistantLocationFnc()

        self._processing = False

    async def _execute_with_lock(self, func, *args, **kwargs):
        """Execute function with lock to prevent concurrent operations"""
        if self._processing:
            return "I'm still processing your previous request. Please wait a moment."
            
        try:
            self._processing = True
            async with self._lock:
                return await func(*args, **kwargs)
        finally:
            self._processing = False

    @llm.ai_callable(
        description="""Search the web for information about a topic.
        This function can be triggered by phrases like:
        - Search for {topic}
        - Find information about {topic}
        - What's the latest on {topic}
        - Tell me about {topic}
        - Look up {topic}"""
    )
    async def web_search(self, topic: str):
        return await self._execute_with_lock(
            self.web_assistant.search, 
            topic
        )

    @llm.ai_callable(
        description="""Read and explain the content from a specific website URL.
        This function can be triggered by phrases like:
        - Read website {url}
        - What does {url} say about {topic}
        - Explain the content at {url}
        - Summarize {url}
        Optional: Include a specific topic to focus on."""
    )
    async def web_read(self, url: str, topic: str = None):
        search_context = None
        if self.web_assistant.last_search_results:
            search_context = "Following up on search about: " + \
                           self.web_assistant.last_search_results[0].get('title', '')
        
        return await self._execute_with_lock(
            self.web_assistant.traverse_web,
            url, topic, search_context
        )

    @llm.ai_callable(
        description="""Read more details about a specific search result from the previous search.
        This function can be triggered by phrases like:
        - Tell me more about result {result_number}
        - Open result {result_number}
        - What's in result {result_number}
        - Show me result {result_number}
        Note: Results are numbered starting from 1"""
    )
    async def read_search_result(self, result_number: int):
        if not self.web_assistant.last_search_results:
            return "I don't have any recent search results to reference. Please perform a search first."
        
        if result_number < 1 or result_number > len(self.web_assistant.last_search_results):
            return f"Please specify a result number between 1 and {len(self.web_assistant.last_search_results)}"
        
        return await self._execute_with_lock(
            self.web_assistant.get_site_from_results,
            result_number - 1
        )

    @llm.ai_callable(
        description="""Explain what's currently visible on the screen.
        This function can be triggered by phrases like:
        - What's on my screen
        - Explain what I'm looking at
        - Read my screen
        - What do you see
        - Describe my screen"""
    )
    async def explain_screen(self):
        return await self._execute_with_lock(
            self.screen_assistant.explain_concept
        )

    @llm.ai_callable(
        description="""List the most recent search results.
        This function can be triggered by phrases like:
        - Show search results
        - What were the results
        - List the results
        - Show me what you found"""
    )
    async def list_search_results(self):
        if not self.web_assistant.last_search_results:
            return "I don't have any recent search results to show. Please perform a search first."
        
        results = []
        for i, result in enumerate(self.web_assistant.last_search_results, 1):
            results.append(f"{i}. {result.get('title', 'Untitled')}")
        
        return "Here are the recent search results:\n" + "\n".join(results)

    async def cleanup(self):
        """Cleanup all resources"""
        try:
            if hasattr(self.web_assistant, 'cleanup'):
                await self.web_assistant.cleanup()
            if hasattr(self.location_assistant, 'cleanup'):
                await self.location_assistant.cleanup()
            logger.info("Agent functions cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")