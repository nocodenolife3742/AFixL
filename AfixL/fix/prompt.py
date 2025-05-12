from AfixL.fuzz.crash import Crash


# TODO: All things may be moved to the prompt.py file


class Prompt:
    def __init__(self, prompt: str):
        self.prompt = prompt

    def __str__(self):
        return self.prompt

    def __repr__(self):
        return f"Prompt({self.prompt})"


def generate_prompt(
    crash: Crash,
) -> Prompt:
    """
    Generate a prompt for the LLM based on the crash information.

    Args:
        crash (Crash): The crash object containing information about the crash.

    Returns:
        Prompt: The generated prompt for the LLM.
    """
    prompt = f"""
    You are a code repair assistant. Your task is to fix the following code crash.
    The crash from AddressSanitizer or UndefinedBehaviorSanitizer is as follows:
    {crash.input_content}

    You have two operations to choose from:
    1. Fix the code by modifying the source code. The operation should be done in the following way:
        - Use the diff format to show the changes made to the code.
        - The diff format should be in the following format:
            --- original_file
            +++ fixed_file
            @@ -1,2 +1,2 @@
            - original_code
            + fixed_code
        - The operation should 
    2. Get the source code of the program.
    
    Please provide a detailed explanation of the crash and suggest a fix.
    """
    return Prompt(prompt)
