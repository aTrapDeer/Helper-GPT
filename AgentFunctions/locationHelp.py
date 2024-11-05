from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
import logging
from dotenv import load_dotenv
import os
import re
from datetime import datetime
import aiohttp

load_dotenv()
MAPQUEST_API_KEY = os.getenv("MAPQUEST_API_KEY") 



# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logger with both file and console handlers
logger = logging.getLogger("LocationHelp")
logger.setLevel(logging.INFO)

# Create formatters and handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler - logs/web_search_YYYY-MM-DD.log
file_handler = logging.FileHandler(
    f'logs/LocationHelp_{datetime.now().strftime("%Y-%m-%d")}.log',
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Add both handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)


class AssistantLocationFnc:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="HelpMeGPT")
        self._cache = {}

    async def get_location_info(self, place: str, address_data: dict = None):
        """Get location information optimized for MapQuest"""
        logger.info(f"Getting location info for: {place}")
        try:
            cache_key = f"{place}_{hash(str(address_data))}"
            if cache_key in self._cache:
                return self._cache[cache_key]

            # Use structured address data if available
            if address_data and isinstance(address_data, dict):
                search_query = address_data.get("formatted_address", place)
            else:
                search_query = place

            location = self.geolocator.geocode(search_query)

            if not location:
                return {
                    "error": "Location not found",
                    "query": place
                }

            # Format for MapQuest compatibility
            location_info = {
                "name": place,
                "address": location.address,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "street": address_data.get("street_address", "") if address_data else "",
                "city": address_data.get("city", "") if address_data else "",
                "state": address_data.get("state", "") if address_data else "",
                "postal_code": address_data.get("postal_code", "") if address_data else "",
                "mapquest_formatted": self._format_mapquest_address(location)
            }

            self._cache[cache_key] = location_info
            return location_info

        except Exception as e:
            logger.error(f"Error getting location info: {str(e)}", exc_info=True)
            return {"error": str(e), "query": place}

    def _format_mapquest_address(self, location_info: dict) -> str:
        """Format address for MapQuest API - simplified"""
        return location_info.get("address", "")

    async def get_directions(self, origin_info: dict, dest_info: dict, mode: str = "driving"):
        """Get directions using MapQuest"""
        logger.info(f"Getting directions from {origin_info.get('name')} to {dest_info.get('name')}")
        
        try:
            if "error" in origin_info or "error" in dest_info:
                return "Couldn't get directions due to location lookup errors."

            url = f"http://www.mapquestapi.com/directions/v1/route?key={MAPQUEST_API_KEY}"
            
            # Simplified payload
            payload = {
                "locations": [
                    origin_info.get("address", ""),
                    dest_info.get("address", "")
                ],
                "options": {
                    "routeType": mode.upper(),
                    "narrativeType": "text",
                    "unit": "m",
                    "enhancedNarrative": True,
                    "avoidTimedConditions": True
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    data = await response.json()
                    
                    if data["info"]["statuscode"] == 0:
                        route = data["route"]
                        return {
                            "distance": route["distance"],
                            "time": route["formattedTime"],
                            "steps": [m["narrative"] for m in route["legs"][0]["maneuvers"]],
                            "formatted_response": self._format_directions_response(
                                origin_info["name"],
                                dest_info["name"],
                                route
                            )
                        }
                    else:
                        return "Couldn't calculate directions. Please check the addresses."

        except Exception as e:
            logger.error(f"Error getting directions: {str(e)}", exc_info=True)
            return f"Sorry, I encountered an error getting directions: {str(e)}"

    def _format_directions_response(self, origin_name: str, dest_name: str, route: dict) -> str:
        """Format the directions response nicely"""
        response = [
            f"Directions from {origin_name} to {dest_name}:",
            f"Total Distance: {route['distance']:.1f} miles",
            f"Estimated Time: {route['formattedTime']}",
            "\nStep by Step Directions:"
        ]
        
        for i, step in enumerate(route["legs"][0]["maneuvers"], 1):
            response.append(f"{i}. {step['narrative']}")
            
        return "\n".join(response)

    async def get_distance(self, origin_info: dict, dest_info: dict):
        """Calculate distance between two locations"""
        try:
            if "error" in origin_info or "error" in dest_info:
                return "Couldn't calculate distance due to location lookup errors."

            origin_coords = (origin_info.get("latitude"), origin_info.get("longitude"))
            dest_coords = (dest_info.get("latitude"), dest_info.get("longitude"))

            if None in origin_coords or None in dest_coords:
                return "Couldn't calculate distance due to missing coordinates."

            distance = geodesic(origin_coords, dest_coords).miles
            return f"The distance between {origin_info.get('name')} and {dest_info.get('name')} is {distance:.1f} miles."

        except Exception as e:
            logger.error(f"Error calculating distance: {str(e)}", exc_info=True)
            return f"Sorry, I encountered an error calculating the distance: {str(e)}"
