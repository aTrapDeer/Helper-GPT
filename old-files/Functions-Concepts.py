
  ### Will need re-write this code

    # @llm.ai_callable(
    #     description="""Find location or address information.
    #     This function can be triggered by phrases like:
    #     - Where is {place}
    #     - What's the address of {place}
    #     - Find location of {place}
    #     - Get address for {place}"""
    # )
    # async def find_location(self, place: str):
    #     try:
    #         # Immediate feedback
    #         logger.info(f"Looking up location for: {place}")
            
    #         # First try web search for context
    #         search_result = await self._execute_with_lock(
    #             self.web_assistant.search_location,
    #             place
    #         )
            
    #         if isinstance(search_result, dict) and "error" in search_result:
    #             logger.warning(f"Web search failed: {search_result['error']}")
    #             # Try direct location lookup as fallback
    #             return await self._execute_with_lock(
    #                 self.location_assistant.get_location_info,
    #                 place
    #             )
            
    #         # Get precise location with search context
    #         return await self._execute_with_lock(
    #             self.location_assistant.get_location_info,
    #             place,
    #             search_result
    #         )

    #     except Exception as e:
    #         logger.error(f"Error in find_location: {str(e)}", exc_info=True)
    #         return {"error": str(e), "query": place}

    # @llm.ai_callable(
    #     description="""Calculate distance between two locations.
    #     This function can be triggered by phrases like:
    #     - How far is {origin} from {destination}
    #     - Distance between {origin} and {destination}
    #     - How long to drive from {origin} to {destination}
    #     - What's the distance to {destination} from {origin}"""
    # )
    # async def calculate_distance(self, origin: str, destination: str):
    #     # Get location info first
    #     origin_info = await self.find_location(origin)
    #     dest_info = await self.find_location(destination)
        
    #     return await self._execute_with_lock(
    #         self.location_assistant.get_distance,
    #         origin_info,
    #         dest_info
    #     )

    # @llm.ai_callable(
    #     description="""Get directions between two locations.
    #     This function can be triggered by phrases like:
    #     - How do I get to {destination} from {origin}
    #     - Directions from {origin} to {destination}
    #     - Navigate to {destination} from {origin}
    #     - What's the best route from {origin} to {destination}
    #     Supports modes: driving (default), walking, bicycling, transit"""
    # )
    # async def get_directions(self, origin: str, destination: str, mode: str = "driving"):
    #     try:
    #         # Immediate feedback
    #         yield "I'm looking up the locations and calculating directions. This might take a moment..."
            
    #         # Get location info first
    #         origin_info = await self.find_location(origin)
    #         if "error" in origin_info:
    #             yield f"Could not find location for '{origin}'. Please try a more specific address."
    #             return
                
    #         yield f"Found {origin}. Looking up destination..."
            
    #         dest_info = await self.find_location(destination)
    #         if "error" in dest_info:
    #             yield f"Could not find location for '{destination}'. Please try a more specific address."
    #             return
                
    #         yield "Found both locations. Calculating route..."
            
    #         # Validate travel mode
    #         valid_modes = ["driving", "walking", "bicycling", "transit"]
    #         mode = mode.lower()
    #         if mode not in valid_modes:
    #             mode = "driving"
            
    #         result = await self._execute_with_lock(
    #             self.location_assistant.get_directions,
    #             origin_info,
    #             dest_info,
    #             mode
    #         )
            
    #         if isinstance(result, dict) and "formatted_response" in result:
    #             yield result["formatted_response"]
    #         else:
    #             yield result
                
    #     except Exception as e:
    #         logger.error(f"Error in get_directions: {str(e)}", exc_info=True)
    #         yield "Sorry, I encountered an error while getting directions. Please try again."

    