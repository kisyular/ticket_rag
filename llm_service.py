"""
LLM Service for generating responses from retrieved tickets
Uses Ollama for local LLM inference
"""
import requests
from typing import List, Dict, Any, Optional
import json


class LocalLLMService:
    """
    Service for generating responses using locally running Ollama
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        """
        Initialize LLM service
        
        Args:
            base_url: Ollama API endpoint
            model: Model name to use (llama2, mistral, codellama, etc.)
        """
        self.base_url = base_url
        self.model = model
        self.api_url = f"{base_url}/api/generate"
    
    def check_ollama_running(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def generate_answer(
        self, 
        query: str, 
        context_tickets: List[Dict[str, Any]],
        stream: bool = False
    ):
        """
        Generate an answer based on query and retrieved ticket context

        Args:
            query: User's question
            context_tickets: List of relevant tickets from RAG search
            stream: Whether to stream the response

        Returns:
            Generated answer string (if stream=False) or generator (if stream=True)
        """
        if not self.check_ollama_running():
            return (
                "Ollama is not running. Please start Ollama first:\n"
                "1. Install: https://ollama.ai/download\n"
                "2. Run: ollama run llama2\n\n"
                "Showing raw search results instead:\n\n" +
                self._format_fallback_response(context_tickets)
            )

        # Build context from retrieved tickets
        context = self._build_context(context_tickets)

        # Create prompt
        prompt = self._create_prompt(query, context)

        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": stream,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500
                    }
                },
                timeout=60,
                stream=stream
            )

            if response.status_code == 200:
                if stream:
                    # Return generator for streaming
                    return self._stream_response(response)
                else:
                    result = response.json()
                    return result.get('response', 'No response generated')
            else:
                return f"Error: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Error generating response: {str(e)}\n\nFalling back to search results:\n\n{self._format_fallback_response(context_tickets)}"

    def _stream_response(self, response):
        """
        Generator that yields response chunks as they arrive from Ollama

        Args:
            response: Streaming HTTP response from Ollama

        Yields:
            Text chunks from the LLM
        """
        import json

        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if 'response' in chunk:
                        yield chunk['response']
                except json.JSONDecodeError:
                    continue

    def _build_context(self, tickets: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved tickets"""
        if not tickets:
            return "No relevant tickets found."

        context_parts = []
        for i, ticket in enumerate(tickets, 1):
            metadata = ticket.get('metadata', {})
            content = ticket.get('content', '')
            relevance = ticket.get('relevance_score', 0)

            context_parts.append(
                f"--- Ticket {i} (Relevance: {relevance:.2%}) ---\n"
                f"{content}\n"
            )

        return "\n".join(context_parts)

    def _create_prompt(self, query: str, context: str) -> str:
        """Create the prompt for the LLM"""
        prompt = f"""You are a helpful assistant that answers questions about support tickets.

Context (Retrieved Tickets):
{context}

User Question: {query}

Instructions:
- Answer based ONLY on the information in the retrieved tickets above
- Be concise and specific
- If the tickets don't contain relevant information, say so
- Include ticket numbers when referencing specific tickets
- If multiple tickets are relevant, summarize the key points

Answer:"""

        return prompt

    def _format_fallback_response(self, tickets: List[Dict[str, Any]]) -> str:
        """Format tickets as fallback when LLM is unavailable"""
        if not tickets:
            return "No relevant tickets found."

        response = "Found relevant tickets:\n\n"
        for i, ticket in enumerate(tickets, 1):
            metadata = ticket.get('metadata', {})
            relevance = ticket.get('relevance_score', 0)

            response += (
                f"{i}. Ticket #{metadata.get('ticket_id', 'N/A')} "
                f"(Relevance: {relevance:.2%})\n"
                f"   Title: {metadata.get('title', 'N/A')}\n"
                f"   Status: {metadata.get('status', 'N/A')}\n"
                f"   Priority: {metadata.get('priority', 'N/A')}\n"
                f"   Assigned to: {metadata.get('assigned_to', 'N/A')}\n\n"
            )

        return response


class MockLLMService(LocalLLMService):
    """
    Mock LLM service for testing without Ollama
    Returns formatted search results instead of generated text
    """

    def __init__(self):
        super().__init__()

    def generate_answer(
        self,
        query: str,
        context_tickets: List[Dict[str, Any]],
        stream: bool = False
    ) -> str:
        """Return formatted search results"""
        if not context_tickets:
            return f"I couldn't find any tickets relevant to: '{query}'"

        # Create a simple summary
        response = f"Based on your query '{query}', I found {len(context_tickets)} relevant ticket(s):\n\n"

        for i, ticket in enumerate(context_tickets, 1):
            metadata = ticket.get('metadata', {})
            relevance = ticket.get('relevance_score', 0)

            response += (
                f"{i}. **Ticket #{metadata.get('ticket_id', 'N/A')}** - {metadata.get('title', 'N/A')}\n"
                f"   - Status: {metadata.get('status', 'N/A')}\n"
                f"   - Priority: {metadata.get('priority', 'N/A')}\n"
                f"   - Assigned to: {metadata.get('assigned_to', 'N/A')}\n"
                f"   - Relevance: {relevance:.1%}\n\n"
            )

        return response