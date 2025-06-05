# client.py
# This script implements an MCP (Meta-protocol Communication Platform) client
# to interact with the MCP server defined in `server.py`.
# It demonstrates how to connect to the server, list available tools and resources,
# and call tools with parameters, including those interacting with a database and
# an external API.

import asyncio
import re # For parsing note ID from server responses
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

# Define the parameters for starting the MCP server using stdio.
# The client will run `python server.py` to start the server.
server_params = StdioServerParameters(command="python", args=["server.py"])

async def main():
    """
    Main asynchronous function to run the MCP client and interact with the server.
    """
    try:
        # Establish a connection to the server using stdio_client.
        # This context manager handles starting and stopping the server process.
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("Attempting to connect to MCP server via stdio...")
            # Create an MCP client session using the read and write streams.
            async with ClientSession(read_stream, write_stream) as session:
                print("Initializing session...")
                await session.initialize() # Initialize the MCP session
                print("MCP Session initialized successfully.")

                # --- List Tools and Resources ---
                print("\n--- Listing Tools and Resources ---")
                tools = await session.list_tools()
                print("Available tools:", tools)
                resources = await session.list_resources()
                print("Available resources:", resources)

                # --- Interact with fact_resource ---
                # This demonstrates reading from an MCP resource.
                print("\n--- Interacting with fact_resource ---")
                print("Reading fact resource (fact://random)...")
                content, mime_type = await session.read_resource("fact://random")
                print(f"Fact from resource: {content} (MIME: {mime_type})")

                # --- Interact with get_public_fact tool ---
                # This demonstrates calling an MCP tool that fetches data from an external API.
                print("\n--- Interacting with get_public_fact tool ---")
                print("Calling get_public_fact tool...")
                fact_result = await session.call_tool("get_public_fact")
                print(f"Fact from tool: {fact_result}")

                # --- Interact with manage_note tool ---
                # This section demonstrates multiple interactions with the 'manage_note' tool,
                # covering add, list, view, and delete operations on notes.
                print("\n--- Interacting with manage_note tool ---")
                note_id_to_test = None

                # Add a new note
                print("Calling manage_note (add)...")
                add_result = await session.call_tool(
                    "manage_note",
                    {"action": "add", "content": "My first MCP note!"}
                )
                print(f"Add note result: {add_result}")

                # Extract note_id from the server's response string (e.g., "Note added with ID: X")
                # The actual text is in add_result.content[0].text
                add_result_text = ""
                if add_result.content and isinstance(add_result.content, list) and len(add_result.content) > 0:
                    if hasattr(add_result.content[0], 'text'):
                        add_result_text = add_result.content[0].text

                match = re.search(r"ID: (\d+)", add_result_text)
                if match:
                    note_id_to_test = int(match.group(1))
                    print(f"Extracted note ID: {note_id_to_test}")
                else:
                    print("Could not extract note ID from add result. Will try listing.")

                # List notes (to verify the add operation and potentially find the ID)
                print("Calling manage_note (list after add)...")
                list_result_after_add = await session.call_tool("manage_note", {"action": "list"})
                print(f"Notes after add: {list_result_after_add}")

                # Fallback: If ID wasn't parsed from 'add' response, try to infer from 'list'
                # This is less robust and assumes the note is identifiable.
                if note_id_to_test is None and list_result_after_add.content:
                     if list_result_after_add.content and isinstance(list_result_after_add.content, list) and len(list_result_after_add.content) > 0:
                        if hasattr(list_result_after_add.content[0], 'text'):
                            try:
                                import json
                                notes_list_json = json.loads(list_result_after_add.content[0].text)
                                found_note = next((n for n in notes_list_json if n.get("content") == "My first MCP note!"), None)
                                if found_note and 'id' in found_note:
                                    note_id_to_test = found_note['id']
                                    print(f"Inferred note ID from list: {note_id_to_test}")
                            except json.JSONDecodeError:
                                print("Could not parse notes list to infer ID.")


                if note_id_to_test is not None:
                    # View the newly added note
                    print(f"Calling manage_note (view note {note_id_to_test})...")
                    view_result = await session.call_tool(
                        "manage_note",
                        {"action": "view", "note_id": note_id_to_test}
                    )
                    print(f"View note {note_id_to_test} result: {view_result}")

                    # Delete the note
                    print(f"Calling manage_note (delete note {note_id_to_test})...")
                    delete_result = await session.call_tool(
                        "manage_note",
                        {"action": "delete", "note_id": note_id_to_test}
                    )
                    print(f"Delete note {note_id_to_test} result: {delete_result}")

                    # List notes again (to verify the delete operation)
                    print("Calling manage_note (list after delete)...")
                    list_result_after_delete = await session.call_tool("manage_note", {"action": "list"})
                    print(f"Notes after delete: {list_result_after_delete}")

                    # Attempt to view the deleted note (should result in "Note not found")
                    print(f"Calling manage_note (view deleted note {note_id_to_test})...")
                    view_deleted_result = await session.call_tool(
                        "manage_note",
                        {"action": "view", "note_id": note_id_to_test}
                    )
                    print(f"View deleted note {note_id_to_test} result: {view_deleted_result}")
                else:
                    print("Skipping view/delete tests as note_id could not be determined.")

                # --- Interacting with query_codacy tool ---
                print("\n--- Interacting with query_codacy tool ---")
                print("Reminder: Ensure CODACY_API_TOKEN environment variable is set and update placeholder values for provider, organization, and project_name if you want to test against a real project.")

                codacy_provider = "gh"  # Example: 'gh' for GitHub, 'gl' for GitLab, 'bb' for Bitbucket
                codacy_organization = "YOUR_ORG_NAME" # Replace with your actual organization name
                codacy_project_name = "YOUR_REPO_NAME" # Replace with your actual repository name

                # Example: Query for issues
                print(f"\nAttempting to query Codacy for 'issues' for {codacy_organization}/{codacy_project_name}...")
                codacy_issues_result = await session.call_tool(
                    "query_codacy",
                    {
                        "provider": codacy_provider,
                        "organization": codacy_organization,
                        "project_name": codacy_project_name,
                        "metric": "issues"
                    }
                )
                print(f"Codacy 'issues' result: {codacy_issues_result}")

                # Example: Query for coverage
                # Note: Coverage data might only be available if Codacy has processed coverage reports for the project.
                print(f"\nAttempting to query Codacy for 'coverage' for {codacy_organization}/{codacy_project_name}...")
                codacy_coverage_result = await session.call_tool(
                    "query_codacy",
                    {
                        "provider": codacy_provider,
                        "organization": codacy_organization,
                        "project_name": codacy_project_name,
                        "metric": "coverage"
                    }
                )
                print(f"Codacy 'coverage' result: {codacy_coverage_result}")

                # --- Demonstrate manage_note prompting ---
                print("\n--- Demonstrating manage_note server-side prompting ---")
                print("The following call to 'manage_note' is made with no parameters.")
                print("If server-side prompting is working, you should see the server asking for 'action', etc.")
                print("This client is not interactive and will not respond to those prompts.")
                print("The call might result in an error or timeout here, which is expected for this demo.")
                try:
                    # Intentionally call with no parameters to trigger prompts
                    prompt_demo_result = await session.call_tool(
                        "manage_note",
                        {}  # Empty parameters
                    )
                    print(f"Prompt demo call result (if it completed): {prompt_demo_result}")
                except Exception as e_prompt:
                    print(f"Exception during prompt demo call (this might be expected): {e_prompt}")
                print("--- End of manage_note prompting demonstration ---")

                # --- Demonstrate get_prompt for generate_commit_message ---
                print("\n--- Demonstrating get_prompt for 'generate_commit_message' ---")
                example_changes = "Fixed a critical bug in the payment processing module and updated the API documentation accordingly."
                print(f"Requesting 'generate_commit_message' prompt with changes: \"{example_changes}\"")

                try:
                    commit_prompt_result = await session.get_prompt(
                        "generate_commit_message",
                        {"changes": example_changes}
                    )
                    print(f"Prompt Name: generate_commit_message")

                    if commit_prompt_result.messages:
                        print("  Messages from Prompt:")
                        for msg in commit_prompt_result.messages:
                            if hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                print(f"    - Role: {msg.role}, Content: \"{msg.content.text}\"")
                            else:
                                print(f"    - (Message with unexpected structure: {msg})")
                    else:
                        print("  (No messages returned from prompt)")

                except Exception as e_get_prompt:
                    print(f"Error calling get_prompt for 'generate_commit_message': {e_get_prompt}")
                print("--- End of get_prompt demonstration ---")

                # --- Demonstrate ask_openai_llm tool ---
                print("\n--- Demonstrating 'ask_openai_llm' tool ---")
                print("NOTE: This tool requires the OPENAI_API_KEY environment variable to be set.")
                print("If the API key is not set or is invalid, an error message will be shown.")

                example_llm_question = "What are the main benefits of using the Model Context Protocol (MCP)?"
                print(f"Sending question to LLM: \"{example_llm_question}\"")

                try:
                    llm_response = await session.call_tool(
                        "ask_openai_llm",
                        {"question": example_llm_question}
                    )
                    print(f"LLM Response:")
                    # The response is a direct string from the tool if successful,
                    # or an error string from the tool itself.
                    # If session.call_tool itself fails (e.g. tool not found), it would raise an exception.
                    if hasattr(llm_response, 'content') and isinstance(llm_response.content, list) and len(llm_response.content) > 0:
                        if hasattr(llm_response.content[0], 'text'):
                             print(llm_response.content[0].text)
                        else:
                            print(str(llm_response.content[0])) # Fallback for unexpected structure
                    else:
                        print(str(llm_response)) # Fallback if not a typical MCPMessageBlock structure

                except Exception as e_llm_tool:
                    print(f"Error calling 'ask_openai_llm' tool: {e_llm_tool}")
                print("--- End of 'ask_openai_llm' tool demonstration ---")

    except Exception as e:
        print(f"An error occurred in the client: {e}")
        import traceback
        traceback.print_exc()

# Standard Python entry point to run the asyncio event loop with the main function.
if __name__ == "__main__":
    asyncio.run(main())
