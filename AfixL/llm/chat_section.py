from abc import ABC, abstractmethod


class ChatSection(ABC):
    """
    Abstract class for a chat section.
    This class defines the interface for a chat section, which includes methods for
    generating text, getting the model name, and checking if the model is available.
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text based on the provided prompt and previous messages.

        Args:
            prompt (str): The input prompt to generate text from.
            **kwargs: Additional parameters for the generation.

        Returns:
            str: The generated text.
        """
        raise NotImplementedError("Subclasses must implement this method.")
