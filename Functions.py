from AgentFunctions.screenHelp import AssistantScreenFnc
from AgentFunctions.webHelp import AssistantWebFnc
from livekit.agents import llm



class AgentFunctions(llm.FunctionContext):
    def __init__(self) -> None:
        super().__init__()
        self.web_assistant = AssistantWebFnc()

    @llm.ai_callable(
        description="""Explain my screen for me.
        This function can be triggered by phrases like:
        - What's on my screen
        - What's on the screen
        - What is on the screen
        - Describe what you see"""
    )
    async def explain_screen(self):
        return await AssistantScreenFnc().explain_concept()

    @llm.ai_callable(
        description="""Search the web for information about {topic}.
        This function can be triggered by phrases like:
        - Search for {topic}
        - Look up {topic}
        - Find information about {topic}
        - What can you tell me about {topic}"""
    )
    async def web_search(self, topic: str):
        return await self.web_assistant.search(topic)
    
    @llm.ai_callable(
        description="""Read and explain the content from a specific website {url}, optionally focusing on {topic}.
        This function can be triggered by phrases like:
        - Read website {url}
        - What does {url} say
        - Tell me about {url}
        - Explain the content at {url}
        Optionally include a topic focus:
        - What does {url} say about {topic}
        - Tell me about {url}
        - Explain the content at {url}"""
    )
    async def web_read(self, url: str, topic: str = None):
        # If this is following a search, pass the search context
        search_context = None
        if self.web_assistant.last_search_results:
            search_context = "Following up on search about: " + \
                            self.web_assistant.last_search_results[0].get('title', '')
        
        return await self.web_assistant.traverse_web(url, topic, search_context)

    @llm.ai_callable(
        description="""Read more details about search result number {result_number} from the previous search.
        This function can be triggered by phrases like:
        - Tell me more about result {result_number}
        - Read result {result_number}
        - Open result {result_number}
        - What does result {result_number} say"""
    )
    async def read_search_result(self, result_number: int):
        return await self.web_assistant.get_site_from_results(result_number - 1)  # Convert to 0-based index
