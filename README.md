# MCP Server and Client Example

## Description
This project demonstrates a simple MCP (Meta-protocol Communication Platform) server and client setup. The server uses `FastMCP` and includes tools for managing notes in an SQLite database and fetching random facts from a public API. The client interacts with the server to test these functionalities, showcasing basic MCP operations like listing tools/resources and calling tools. Communication between the client and server is handled via stdio.

## Files

-   **`server.py`**:
    -   Implements the MCP server using `FastMCP`.
    -   Provides a `manage_note` tool for CRUD (Create, Read, Update, Delete) operations on notes. Notes are stored in an SQLite database file named `mcp_database.db`. If key parameters like `action`, `note_id` (for view/delete), or `content` (for add) are not provided by the client, the server will prompt for them interactively. `client.py` includes a call that demonstrates this prompting behavior.
    -   Provides a `get_public_fact` tool that fetches a random fact from `https://uselessfacts.jsph.pl/api/v2/facts/random`.
    -   Exposes a `fact://random` resource that also provides a random fact.
    -   Provides a `query_codacy` tool that interacts with the Codacy API (requires `CODACY_API_TOKEN` environment variable to be set). It can fetch project-level code quality metrics such as issues and coverage. Parameters include `provider` (e.g., 'gh'), `organization`, `project_name`, and `metric` (e.g., 'issues', 'coverage').
-   **`client.py`**:
    -   Implements an MCP client to connect to and interact with `server.py`.
    -   It initializes an MCP session, lists available tools and resources.
    -   It tests the `fact://random` resource and the `get_public_fact` tool.
    -   It tests the `manage_note` tool by adding a note, listing notes, viewing the added note, deleting it, and then attempting to view the deleted note.
    -   Demonstrates calling the `query_codacy` tool with example parameters, reminding the user to configure their API token and project details.
-   **`requirements.txt`**:
    -   Contains the list of Python dependencies required to run the project.
-   **`mcp_database.db`**:
    -   This SQLite database file is automatically created by `server.py` when it first runs and is used to store notes. It is not included in the repository but will appear when you run the application.

## Setup & Running

1.  **Install Dependencies:**
    Open your terminal and navigate to the project directory. Then, install the required Python packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set Codacy API Token (Optional for Codacy feature):**
    If you intend to use the `query_codacy` tool, you must set the `CODACY_API_TOKEN` environment variable.
    For Linux/macOS: `export CODACY_API_TOKEN="your_actual_codacy_api_token"`
    For Windows: `set CODACY_API_TOKEN="your_actual_codacy_api_token"`
    Replace `"your_actual_codacy_api_token"` with your personal Codacy API token. The client example also requires you to update placeholder values for provider, organization, and project name to test this feature.

3.  **Run the Client (which starts the Server):**
    Execute the `client.py` script. The client is configured to automatically start the `server.py` script in the background using stdio for communication.
    ```bash
    python client.py
    ```
    You will see output from both the client detailing its actions and results, and some logging from the server in the console.

## Features Demonstrated

-   **MCP `FastMCP` Server Setup:** Basic structure of an MCP server using the `FastMCP` class.
-   **MCP Tools with Parameters:** Definition and usage of tools that accept typed parameters (e.g., `action`, `note_id`, `content` for `manage_note`).
-   **MCP Resources:** Definition and usage of an MCP resource (`fact://random`).
-   **SQLite Database Interaction:** The `manage_note` tool in `server.py` connects to an SQLite database to persist notes.
-   **External API Interaction:** The `get_public_fact` tool in `server.py` makes an asynchronous HTTP request to an external API using `httpx`.
-   **MCP Client Session:** Usage of `ClientSession` to initialize a connection and interact with an MCP server.
-   **Tool and Resource Usage by Client:** Demonstrates `list_tools`, `list_resources`, `read_resource`, and `call_tool`.
-   **Stdio Transport:** The client uses `StdioServerParameters` and `stdio_client` to manage the server lifecycle and communicate with it over standard input/output.
-   **Error Handling:** Basic error handling in server tools (database and API errors) and client-side error printing.
-   **Async Operations:** Use of `async` and `await` for non-blocking operations in both server tools (for API calls) and the client.
