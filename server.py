# server.py
# This script implements an MCP (Meta-protocol Communication Platform) server
# using the FastMCP framework. It provides tools for managing notes stored in an
# SQLite database and for fetching random facts from a public API.
# It also exposes a resource that provides a random fact.

import asyncio
import sqlite3
import httpx
import os
import json # For formatting list of notes as a JSON string
import openai
from mcp.server.fastmcp import FastMCP
from mcp.common.prompt import prompt

DB_NAME = "mcp_database.db"
mcp_server = FastMCP("MyMCPServer")

def init_db():
    """
    Initializes the SQLite database.
    Connects to the database specified by DB_NAME.
    Creates a 'notes' table if it doesn't already exist.
    The 'notes' table has 'id' (INTEGER PRIMARY KEY AUTOINCREMENT) and 'content' (TEXT NOT NULL) columns.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Create the 'notes' table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
    finally:
        if conn:
            conn.close()

init_db()  # Initialize the database when the server starts

@mcp_server.tool()
def manage_note(
    action: str = prompt("Enter the action (e.g., add, view, delete, list):"),
    note_id: int = prompt("Enter the note ID (if action is view/delete):", default=None),
    content: str = prompt("Enter the note content (if action is add):", default=None)
):
    """
    Manages notes stored in the SQLite database.

    Parameters:
    - action (str): The operation to perform. Supported actions:
        - "add": Adds a new note. Requires 'content'.
        - "view": Retrieves a specific note. Requires 'note_id'.
        - "delete": Deletes a specific note. Requires 'note_id'.
        - "list": Lists all notes.
    - note_id (int, optional): The ID of the note for 'view' or 'delete' actions.
    - content (str, optional): The content of the note for the 'add' action.

    Returns:
    - str: A message indicating the result of the operation,
           the content of a note, or a JSON string of all notes.
           Returns an error message if the action is invalid or an error occurs.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        if not action: # Should not happen if prompt is effective and action is not given a default
             return "Error: Action parameter is required."

        if action == "add":
            if not content:
                return "Error: Content is required for 'add' action."
            cursor.execute("INSERT INTO notes (content) VALUES (?)", (content,))
            conn.commit()
            return f"Note added with ID: {cursor.lastrowid}"
        elif action == "view":
            if note_id is None: # Check if note_id is None (it could be if default=None and not provided)
                return "Error: Note ID is required for 'view' action."
            cursor.execute("SELECT content FROM notes WHERE id = ?", (note_id,))
            note = cursor.fetchone()
            return note[0] if note else "Note not found."
        elif action == "delete":
            if note_id is None: # Check if note_id is None
                return "Error: Note ID is required for 'delete' action."
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()
            return f"Note {note_id} deleted." if cursor.rowcount > 0 else "Note not found."
        elif action == "list":
            cursor.execute("SELECT id, content FROM notes")
            notes = cursor.fetchall()
            return json.dumps([{"id": row[0], "content": row[1]} for row in notes])
        else:
            return "Invalid action or missing parameters. Supported actions: add, view, delete, list."

    except sqlite3.Error as e:
        return f"Database error: {e}"
    finally:
        if conn:
            conn.close()

@mcp_server.tool()
async def get_public_fact():
    """
    Fetches a random public fact from the uselessfacts.jsph.pl API.

    Returns:
    - str: The text of a random fact, or an error message if fetching fails.
    """
    try:
        # Use httpx.AsyncClient for asynchronous HTTP requests
        # follow_redirects=True is important as the API might redirect
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en")
            response.raise_for_status()  # Raise an HTTPError for bad responses (4XX or 5XX)
            fact_data = response.json()
            return fact_data.get("text", "Fact not found in response.")
    except httpx.RequestError as e:
        return f"API request error: {e}"
    except Exception as e:  # Catch other potential errors like JSONDecodeError
        return f"Error processing fact: {e}"

@mcp_server.tool()
async def query_codacy(provider: str, organization: str, project_name: str, metric: str = "issues"):
    """
    Queries the Codacy API for code quality metrics.

    Parameters:
    - provider (str): The code hosting provider (e.g., 'gh' for GitHub, 'gl' for GitLab, 'bb' for Bitbucket).
    - organization (str): The organization name on the provider.
    - project_name (str): The name of the repository.
    - metric (str, optional): The metric to query. Supported: "issues", "coverage". Defaults to "issues".

    Returns:
    - dict or str: A dictionary with the API response or an error message string.
    """
    api_token = os.environ.get("CODACY_API_TOKEN")
    if not api_token:
        return "Error: CODACY_API_TOKEN environment variable not set."

    # Construct the API URL based on the metric
    base_url = f"https://api.codacy.com/api/v3/analysis/organizations/{provider}/{organization}/repositories/{project_name}"

    if metric == "issues":
        api_url = f"{base_url}/issues"
    elif metric == "coverage":
        api_url = f"{base_url}/coverage"
    # Add more metrics here as needed.
    # For example, to add commit-specific data:
    # elif metric == "commits":
    #     api_url = f"{base_url}/commits"
    else:
        return f"Error: Unsupported metric '{metric}'. Supported metrics are 'issues', 'coverage'."

    headers = {
        "api-token": api_token,
        "Accept": "application/json"
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4XX or 5XX)
            return response.json()  # Returns the parsed JSON response
    except httpx.RequestError as e:
        return f"API request error: {e}. URL: {api_url}"
    except httpx.HTTPStatusError as e:
        return f"HTTP status error: {e.response.status_code} - {e.response.text}. URL: {api_url}"
    except json.JSONDecodeError: # Although httpx.Response.json() raises its own error for invalid JSON
        return f"Error decoding JSON response from Codacy. URL: {api_url}"
    except Exception as e:
        return f"An unexpected error occurred: {e}. URL: {api_url}"

@mcp_server.resource("fact://random")
async def fact_resource():
    """
    MCP resource that provides a random fact.
    It internally calls the get_public_fact() tool.

    Returns:
    - str: The text of a random fact.
    """
    return await get_public_fact()

@mcp_server.prompt()
def generate_commit_message(changes: str) -> str:
    """
    Generates a structured prompt to help write a commit message based on changes.

    Parameters:
    - changes (str): A description of the changes made.

    Returns:
    - str: A formatted string to guide commit message creation.
    """
    return f"Please write a concise and informative commit message for the following changes: \"{changes}\". Structure it with a short subject line (max 50 chars), a blank line, and then a more detailed body if necessary."

@mcp_server.tool()
async def ask_openai_llm(question: str):
    """
    Sends a question to an OpenAI LLM (gpt-4o-mini) and returns the answer.
    Requires the OPENAI_API_KEY environment variable to be set.

    Parameters:
    - question (str): The question to ask the LLM.

    Returns:
    - str: The LLM's response, or an error message.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "Error: OPENAI_API_KEY environment variable not set."

    client = openai.AsyncOpenAI()

    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": question,
                }
            ],
            model="gpt-4o-mini", # Using a recent and capable model
        )
        if chat_completion.choices and len(chat_completion.choices) > 0:
            message = chat_completion.choices[0].message
            if message and message.content:
                return message.content.strip()
            else:
                return "Error: LLM response was empty or malformed."
        else:
            return "Error: No response choices received from LLM."
    except openai.APIConnectionError as e:
        return f"OpenAI API Connection Error: {e}"
    except openai.RateLimitError as e:
        return f"OpenAI API Rate Limit Error: {e}"
    except openai.AuthenticationError as e:
        return f"OpenAI API Authentication Error: {e}. Check your API key."
    except openai.APIError as e:
        return f"OpenAI API Error: {e}"
    except Exception as e:
        return f"An unexpected error occurred while querying OpenAI: {e}"

# Main execution block to run the MCP server
if __name__ == "__main__":
    print("Starting MCP server...")
    mcp_server.run()
    print("MCP server stopped.")
