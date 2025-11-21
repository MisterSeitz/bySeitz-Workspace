import ollama
import asyncio
import json
from qdrant_client import AsyncQdrantClient

# --- 1. CONFIGURATION ---
OLLAMA_MODEL = 'llama3.1' # IMPORTANT: Use a model that supports tools
QDRANT_URL = "https://5af7f6ce-f007-4f49-aa93-80822ef98354.us-west-1-0.aws.cloud.qdrant.io"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.gPs848DEPrw0kuyLGI7IzlQDLoBNQkpdslKE3u-zLGI" # Your secret Qdrant key
COLLECTION_NAME = "crime_intelligence"
# Use a local embedding model from Ollama
EMBEDDING_MODEL = 'mxbai-embed-large' 

# --- 2. INITIALIZE CLIENTS ---
# We only need the Ollama and Qdrant clients
ollama_client = ollama.AsyncClient()
qdrant_client = AsyncQdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# --- 3. DEFINE YOUR QDRANT FUNCTION (The "Kitchen") ---
# This is the same function as before, but it uses ollama.embeddings
async def search_crime_database(query: str):
    """
    This is the actual function that searches Qdrant.
    """
    print(f"\n[Tool Call: Running search_crime_database with query: '{query}']")
    try:
        # Create an embedding for the user's query using Ollama
        embedding_response = await ollama_client.embeddings(
            model=EMBEDDING_MODEL,
            prompt=query
        )
        query_vector = embedding_response['embedding']

        # --- THIS IS THE CONNECTION ---
        # Your code connects to your Qdrant URL and searches your collection
        search_results = await qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=5, # Get top 5 results
        )
        # ---------------------------------

        # Format the context for the AI
        context = ""
        for result in search_results:
            # We need to parse the JSON strings we stored in the payload
            entities = json.loads(result.payload.get('entities', '{}'))
            
            context += f"--- CONTEXT CHUNK ---\n"
            context += f"Source: {result.payload.get('source_url', 'N/A')}\n"
            context += f"Title: {result.payload.get('title', 'N/A')}\n"
            context += f"Content: {result.payload.get('text_chunk', 'N/A')}\n"
            context += f"Relevant Entities: {json.dumps(entities, indent=2)}\n\n"
        
        print(f"[Tool Call: Found {len(search_results)} results.]")
        return context
    
    except Exception as e:
        print(f"[Tool Call: Error: {e}]")
        return f"An error occurred while searching the database: {e}"

# --- 4. DEFINE THE TOOL FOR OLLAMA (The "Menu") ---
# This is the same JSON you used for OpenAI, just as a Python dict
my_tools = [
  {
    'type': 'function',
    'function': {
      'name': 'search_crime_database',
      'description': 'Searches the South African crime intelligence vector database (Qdrant) for specific information. Use this for any questions about crime statistics, specific reports (like the Tembisa report), people, or locations in South Africa.',
      'parameters': {
        'type': 'object',
        'properties': {
          'query': {
            'type': 'string',
            'description': 'The specific search query to find relevant information in the vector database. For example: "What were the findings of the Tembisa report?"'
          }
        },
        'required': ['query']
      }
    }
  }
]

# --- 5. MAIN APPLICATION LOOP (The "Waiter") ---
async def main():
    
    user_query = "What were the findings of the Tembisa report and what is the population of Gauteng?"
    
    # We must manage the conversation history ourselves
    message_history = [
        {'role': 'user', 'content': user_query}
    ]
    
    print(f"--- Query: {user_query} ---")
    
    # First call to Ollama, providing tools
    response = await ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=message_history,
        tools=my_tools
    )
    
    # Add the AI's first (tool_call) response to the history
    message_history.append(response['message'])
    
    # Check if the model wants to use a tool
    if response['message'].get('tool_calls'):
        print("[Status: Tool call required...]")
        
        # In a real app, you might loop over multiple tool calls
        tool_call = response['message']['tool_calls'][0]
        function_name = tool_call['function']['name']
        arguments = tool_call['function']['arguments']
        
        if function_name == 'search_crime_database':
            # Call our local Qdrant function
            context_string = await search_crime_database(arguments.get('query'))
            
            # Add the tool's result to the history
            message_history.append({
                'role': 'tool',
                'content': context_string,
            })
            
            # Call Ollama AGAIN with the new context
            print("[Status: Submitting context to Ollama...]")
            final_response = await ollama_client.chat(
                model=OLLAMA_MODEL,
                messages=message_history
            )
            
            print("\n--- AI Answer ---")
            print(final_response['message']['content'])
    
    else:
        # The model answered directly (no tool needed)
        print("\n--- AI Answer (Direct) ---")
        print(response['message']['content'])

if __name__ == "__main__":
    # Make sure Ollama is running before you start this script!
    # (e.g., run `ollama serve` in your terminal)
    asyncio.run(main())