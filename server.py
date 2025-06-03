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
from mcp.server.fastmcp import FastMCP

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
def manage_note(action: str, note_id: int = None, content: str = None):
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

        if action == "add" and content:
            cursor.execute("INSERT INTO notes (content) VALUES (?)", (content,))
            conn.commit()
            return f"Note added with ID: {cursor.lastrowid}"
        elif action == "view" and note_id is not None:
            cursor.execute("SELECT content FROM notes WHERE id = ?", (note_id,))
            note = cursor.fetchone()
            return note[0] if note else "Note not found."
        elif action == "delete" and note_id is not None:
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()
            return f"Note {note_id} deleted." if cursor.rowcount > 0 else "Note not found."
        elif action == "list":
            cursor.execute("SELECT id, content FROM notes")
            notes = cursor.fetchall()
            # Return a JSON string representing the list of notes
            return json.dumps([{"id": row[0], "content": row[1]} for row in notes])
        else:
            return "Invalid action or missing parameters."

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

@mcp_server.resource("fact://random")
async def fact_resource():
    """
    MCP resource that provides a random fact.
    It internally calls the get_public_fact() tool.

    Returns:
    - str: The text of a random fact.
    """
    return await get_public_fact()

# Main execution block to run the MCP server
if __name__ == "__main__":
    print("Starting MCP server...")
    mcp_server.run()
    print("MCP server stopped.")
