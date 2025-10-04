# AFixL

> A Conversational Large Language Model Agent for Automated Program Repair Guided by Fuzzing

## Prerequisites

Ensure the following are installed on your system:
- [uv](https://github.com/astral-sh/uv)
- [docker](https://www.docker.com/)

## Getting Started

Follow these steps to set up and run the project:

1. **Clone the Repository**  
    Clone the repository to your local machine:
    ```bash
    git clone https://github.com/nocodenolife3742/AFixL.git afixl
    cd afixl
    ```

2. **Set Up Environment Variables**  
    Export your Google API key:
    ```bash
    export GOOGLE_API_KEY=<your_api_key>
    ```

3. **Run the Application**  
    Use `uv` to run the application:
    ```bash
    uv run main.py --path ./example/
    ```
