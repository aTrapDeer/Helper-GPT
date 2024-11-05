#this will be funcitons for handling web requests and responses our agent will make
import os
import requests
from openai import OpenAI
from dotenv import load_dotenv
import logging
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from .screenHelp import encode_image
# Traversing Imports
import time 
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tempfile
import pytz
import re



# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logger with both file and console handlers
logger = logging.getLogger("WebHelp")
logger.setLevel(logging.INFO)

# Create formatters and handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler - logs/web_search_YYYY-MM-DD.log
file_handler = logging.FileHandler(
    f'logs/web_search_{datetime.now().strftime("%Y-%m-%d")}.log',
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

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)
searchKey = os.getenv("WEB_SEARCH_API_KEY")
searchEngine = os.getenv("SEARCH_ENGINE_ID")


class AssistantWebFnc:
    def __init__(self) -> None:
        self.last_search_results = []
        self._cache = {}
        self.client = OpenAI()
        self.setup_selenium()
        self.timezone = pytz.timezone('America/Chicago')  # Set your timezone
        
    def setup_selenium(self):
        """Setup headless Chrome browser"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def process_date_keywords(self, topic: str) -> str:
        """Convert relative date keywords to actual dates"""
        current_date = datetime.now(self.timezone)
        
        # Dictionary of date keywords and their timedelta
        date_keywords = {
            r'\btoday\b': (current_date, ""),
            r'\btomorrow\b': (current_date + timedelta(days=1), ""),
            r'\byesterday\b': (current_date - timedelta(days=1), ""),
            r'\blast week\b': (current_date - timedelta(weeks=1), ""),
            r'\bnext week\b': (current_date + timedelta(weeks=1), ""),
            r'\blast month\b': (current_date - timedelta(days=30), ""),
            r'\bthis month\b': (current_date, ""),
        }
        
        modified_topic = topic.lower()
        for keyword, (date_obj, suffix) in date_keywords.items():
            if re.search(keyword, modified_topic):
                formatted_date = date_obj.strftime("%B %d, %Y")
                modified_topic = re.sub(keyword, formatted_date + suffix, modified_topic)
                logger.info(f"Converted date keyword to: {formatted_date}")
                
        return modified_topic

    async def search(self, topic: str):
        logger.info(f"Starting web search for topic: {topic}")
        try:
            # Process any date keywords in the topic
            processed_topic = self.process_date_keywords(topic)
            logger.info(f"Processed topic with dates: {processed_topic}")
            
            self.last_search_results = searchFunction(processed_topic)
            logger.info(f"Found {len(self.last_search_results)} search results")
            
            # Pass both original and processed topics for context
            message = explain_with_ai(processed_topic, self.last_search_results, original_query=topic)
            logger.info("Successfully generated AI explanation")
            return message
        except Exception as e:
            logger.error(f"Error in search function: {str(e)}", exc_info=True)
            return f"Sorry, I encountered an error while searching: {str(e)}"
        
    async def traverse_web(self, url: str, topic: str = None, search_context: str = None):
        logger.info(f"Traversing webpage: {url}")
        try:
            # First try normal request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 403:
                logger.info("403 error encountered, attempting screenshot method")
                return await self.screenshot_and_analyze(url, topic)
                
            # If successful, continue with normal parsing
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            content = extract_content(soup)
            
            if topic:
                relevant_sections = find_relevant_sections(soup, topic)
                content['topic_specific'] = relevant_sections
            
            explanation = explain_webpage_content(
                content, 
                topic=topic,
                search_context=search_context
            )
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error in normal traversal, attempting screenshot method: {str(e)}")
            return await self.screenshot_and_analyze(url, topic)

    async def screenshot_and_analyze(self, url: str, topic: str = None):
        """Take screenshot of webpage and analyze it"""
        try:
            logger.info(f"Taking screenshot of {url}")
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Scroll to capture full page
            height = self.driver.execute_script("return document.body.scrollHeight")
            self.driver.set_window_size(1920, height)
            
            # Save screenshot to temporary file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                self.driver.save_screenshot(tmp.name)
                screenshot_path = tmp.name
            
            # Use existing image analysis function
            message = explain_with_ai_screenshot(
                screenshot_path, 
                topic=topic,
                url=url
            )
            
            # Clean up
            os.unlink(screenshot_path)
            
            return message
            
        except Exception as e:
            logger.error(f"Error in screenshot method: {str(e)}", exc_info=True)
            return f"Sorry, I couldn't access this webpage: {str(e)}"
        
    def __del__(self):
        """Clean up Selenium driver"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    async def get_site_from_results(self, result_number: int):
        if 0 <= result_number < len(self.last_search_results):
            url = self.last_search_results[result_number]['link']
            return await self.traverse_web(url)
        return "Sorry, that result number is not available."

    async def cleanup(self):
        """Cleanup resources"""
        try:
            self._cache.clear()
            self.last_search_results.clear()
            # Add any other cleanup needed
            logger.info("Web assistant cleanup completed")
        except Exception as e:
            logger.error(f"Error during web assistant cleanup: {str(e)}")

def searchFunction(inquiry):
    logger.info(f"Executing Google search for: {inquiry}")
    try:
        service = build(
            "customsearch", "v1", developerKey=searchKey
        )

        res = (
            service.cse()
            .list(
                q=inquiry,
                cx=searchEngine,
                num=10
            )
            .execute()
        )
        
        formatted_results = []
        for item in res.get('items', []):
            formatted_results.append({
                'title': item.get('title', ''),
                'snippet': item.get('snippet', ''),
                'link': item.get('link', '')
            })
        
        logger.info(f"Search completed successfully with {len(formatted_results)} results")
        return formatted_results
    except Exception as e:
        logger.error(f"Search function error: {str(e)}", exc_info=True)
        raise

# Explaining the video found from search restults
def VideoExplainFunction(searchResults):
    logger.info("Explaining video search results")
    webInformation = [] # infromation scrapped from the site
    return webInformation


def explain_with_ai(inquiry, searchResults, original_query=None):
    logger.info(f"Starting AI explanation for search: {inquiry}")
    
    # Convert searchResults to a more readable format
    formatted_text = ""
    for result in searchResults:
        formatted_text += f"\nTitle: {result['title']}\nSummary: {result['snippet']}\nLink: {result['link']}\n"

    # Add date context to the system message
    current_date = datetime.now().strftime("%B %d, %Y")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": f"You are a helpful assistant explaining web search results. Today's date is {current_date}. Be concise but informative - try to interpret the information. Don't say the URLs outloud."
            },
            {
                "role": "user",
                "content": f"Based on the search for '{inquiry}' (original query: '{original_query if original_query else inquiry}'), here are the results:\n{formatted_text}\n\nPlease provide a clear summary of the most relevant information answering the inquiry, considering today's date is {current_date}."
            }
        ],
        "max_tokens": 2500
    }

    try:
        logger.info("Sending request to OpenAI API")
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        logger.info("Successfully received AI explanation")
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
        return f"An error occurred while processing the search results: {str(e)}"

def extract_content(soup):
    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'footer']):
        element.decompose()
        
    content = {
        'title': soup.title.string if soup.title else '',
        'headings': [h.get_text().strip() for h in soup.find_all(['h1', 'h2', 'h3'])],
        'paragraphs': [p.get_text().strip() for p in soup.find_all('p') if p.get_text().strip()],
        'lists': [li.get_text().strip() for li in soup.find_all('li') if li.get_text().strip()]
    }
    
    return content

def gen_explain_openai(prompt, formatted_content, content_type="webpage", search_context=None):
    logger.info(f"Starting AI explanation for {content_type}: {prompt}")
    
    # Customize system prompt based on content type
    system_prompts = {
        "webpage": """You are an expert at explaining webpage content. Focus on:
            1. Main ideas and key points
            2. Relevant details about the specific topic if provided
            3. Important facts and figures
            4. Clear structure and flow
            Avoid mentioning URLs or technical details unless specifically relevant.""",
        
        "search": """You are an expert at analyzing search results. Focus on:
            1. Most relevant findings
            2. Comparing different sources
            3. Highlighting consensus and disagreements
            4. Suggesting which results might be most useful
            Don't mention URLs unless specifically asked."""
    }

    # Build context-aware prompt
    context_builder = {
        "title": formatted_content.get('title', ''),
        "main_content": formatted_content.get('content', ''),
        "search_context": search_context if search_context else None,
        "topic_focus": prompt
    }

    payload = {
        "model": "gpt-4o-mini",  # Updated to latest model
        "messages": [
            {
                "role": "system",
                "content": system_prompts.get(content_type, system_prompts["webpage"])
            },
            {
                "role": "user",
                "content": f"""Context: {context_builder['search_context'] if context_builder['search_context'] else 'Direct webpage analysis'}
                Topic: {context_builder['topic_focus']}
                Content: {context_builder['main_content']}
                
                Please provide a clear, conversational explanation focusing on the most relevant information for this topic."""
            }
        ],
        "max_tokens": 2500,
        "temperature": 0.7  # Add some variety to responses
    }

    try:
        logger.info("Sending request to OpenAI API")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"},
            json=payload
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
        return f"An error occurred while processing the content: {str(e)}"

def find_relevant_sections(soup, topic):
    """Find sections of the webpage most relevant to the topic"""
    relevant_sections = []
    
    # Convert topic to keywords
    keywords = set(topic.lower().split())
    
    # Search through different HTML elements
    for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'li']):
        text = element.get_text().strip().lower()
        # Check if any keyword appears in the text
        if any(keyword in text for keyword in keywords):
            relevant_sections.append({
                'type': element.name,
                'content': element.get_text().strip()
            })
    
    return relevant_sections

def explain_webpage_content(content, topic=None, search_context=None):
    formatted_content = {
        'title': content['title'],
        'content': f"""
        Main Headings:
        {chr(10).join(content['headings'][:5])}
        
        Key Content:
        {chr(10).join(content['paragraphs'][:10])}
        
        {f"Topic-Specific Content ({topic}):" if topic else ""}
        {chr(10).join([section['content'] for section in content.get('topic_specific', [])])}
        """
    }
    
    return gen_explain_openai(
        prompt=topic if topic else "general overview",
        formatted_content=formatted_content,
        content_type="webpage",
        search_context=search_context
    )

def explain_with_ai_screenshot(image_path, topic=None, url=None):
    """Analyze webpage screenshot with GPT-4 Vision"""
    logger.info(f"Analyzing screenshot of webpage: {url}")
    
    base64_image = encode_image(image_path)
    
    context = f"This is a screenshot of {url}. "
    if topic:
        context += f"Please focus on information about {topic}. "
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert at analyzing webpage screenshots and explaining their content clearly and concisely."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{context}Please explain the main content visible in this webpage screenshot."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 2500
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error analyzing screenshot: {str(e)}", exc_info=True)
        return f"An error occurred while analyzing the webpage: {str(e)}"