from AfixL.llm.chat_section import ChatSection
import logging
from google import genai


class Gemini(ChatSection):
    """
    A class to interact with the Gemini API for text generation.
    """

    def __init__(self, api_key: str, model: str):
        """
        Initialize the Gemini class with the API key.

        Args:
            api_key (str): The API key for the Gemini API.
            model (str): The model to use for text generation.
        """
        self.logger = logging.getLogger(__name__)

        # Check if the API key is set
        if not api_key:
            self.logger.error("Gemini API key is not set.")
            raise ValueError("Gemini API key is not set.")
        self.api_key = api_key

        # Check if the model is set
        if not model:
            self.logger.error("Gemini model is not set.")
            raise ValueError("Gemini model is not set.")
        self.model = model

        # Set up the Gemini client and chat session
        self.logger.debug("Setting up Gemini client.")
        self.client = genai.Client(api_key=self.api_key)
        self.logger.debug("Creating chat session.")
        self.chat_session = self.client.chats.create(model=self.model)

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text based on the provided prompt and previous messages.

        Args:
            prompt (str): The input prompt to generate text from.
            **kwargs: Additional parameters for the generation.

        Returns:
            str: The generated text.
        """
        self.logger.debug(f"Generating text with prompt: {prompt}")
        response = self.chat_session.send_message(prompt, **kwargs)
        self.logger.debug(f"Response from Gemini: {response.text}")
        return response.text
