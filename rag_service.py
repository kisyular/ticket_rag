"""
RAG Service for Ticket System
Handles embedding, indexing, and retrieval of tickets
"""
import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime
from typing import List, Dict, Any, Optional
import json


class TicketRAGService:
    """
    Local RAG service for ticket system using:
    - sentence-transformers for embeddings (runs locally)
    - ChromaDB for vector storage (runs locally)
    - Ollama for LLM generation (runs locally)
    """
    
    def __init__(self, collection_name: str = "tickets", model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the RAG service
        
        Args:
            collection_name: Name of the ChromaDB collection
            model_name: Sentence transformer model to use
        """
        # Initialize embedding model (runs locally on CPU/GPU)
        print(f"Loading embedding model: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)
        
        # Initialize ChromaDB (persistent storage)
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
            print(f"Loaded existing collection: {collection_name}")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={
                    "description": "Ticket system embeddings",
                    "hnsw:space": "cosine"  # Use cosine similarity (better for text)
                }
            )
            print(f"Created new collection: {collection_name}")

    def format_ticket_for_embedding(self, ticket_data: Dict[str, Any]) -> str:
        """
        Format ticket data into a searchable text representation

        Args:
            ticket_data: Dictionary containing ticket fields

        Returns:
            Formatted string for embedding
        """
        # Extract fields
        ticket_id = ticket_data.get('id', 'N/A')
        title = ticket_data.get('title', '')
        description = ticket_data.get('ticket_description', '')
        status = ticket_data.get('status', 'N/A')
        priority = ticket_data.get('priority', 'N/A')
        created_by = ticket_data.get('created_by', 'Unknown')
        assigned_to = ticket_data.get('assigned_to', 'Unassigned')
        created_date = ticket_data.get('created_date', '')
        closed_date = ticket_data.get('closed_date', '')
        cc_admins = ticket_data.get('cc_admins', [])
        cc_non_admins = ticket_data.get('cc_non_admins', [])

        # Format date strings
        if isinstance(created_date, datetime):
            created_date = created_date.strftime('%Y-%m-%d')
        if isinstance(closed_date, datetime):
            closed_date = closed_date.strftime('%Y-%m-%d')

        # Create formatted text optimized for semantic search
        formatted_text = f"""
Ticket #{ticket_id}: {title}

Description: {description}

Status: {status}
Priority: {priority}
Created by: {created_by}
Assigned to: {assigned_to}
Created on: {created_date}
{f"Closed on: {closed_date}" if closed_date else "Status: Open"}

CC Admins: {', '.join(cc_admins) if cc_admins else 'None'}
CC Non-Admins: {', '.join(cc_non_admins) if cc_non_admins else 'None'}
        """.strip()

        return formatted_text

    def add_ticket(self, ticket_data: Dict[str, Any]) -> bool:
        """
        Add or update a ticket in the vector database

        Args:
            ticket_data: Dictionary containing ticket fields

        Returns:
            True if successful
        """
        try:
            ticket_id = str(ticket_data['id'])
            formatted_text = self.format_ticket_for_embedding(ticket_data)

            # Generate embedding
            embedding = self.embedding_model.encode(formatted_text).tolist()

            # Store metadata separately for filtering
            metadata = {
                'ticket_id': ticket_id,
                'title': ticket_data.get('title', ''),
                'status': ticket_data.get('status', ''),
                'priority': ticket_data.get('priority', ''),
                'created_by': ticket_data.get('created_by', ''),
                'assigned_to': ticket_data.get('assigned_to', ''),
                'created_date': str(ticket_data.get('created_date', '')),
            }

            # Add to ChromaDB (upsert - updates if exists)
            self.collection.upsert(
                ids=[ticket_id],
                embeddings=[embedding],
                documents=[formatted_text],
                metadatas=[metadata]
            )

            print(f"Added/Updated ticket #{ticket_id}")
            return True

        except Exception as e:
            print(f"Error adding ticket: {e}")
            return False

    def add_tickets_bulk(self, tickets_data: List[Dict[str, Any]]) -> int:
        """
        Add multiple tickets in bulk

        Args:
            tickets_data: List of ticket dictionaries

        Returns:
            Number of tickets successfully added
        """
        success_count = 0
        for ticket_data in tickets_data:
            if self.add_ticket(ticket_data):
                success_count += 1

        print(f"Successfully added {success_count}/{len(tickets_data)} tickets")
        return success_count

    def search_tickets(
        self,
        query: str,
        n_results: int = 5,
        filter_status: Optional[str] = None,
        filter_priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant tickets using semantic search

        Args:
            query: Natural language search query
            n_results: Number of results to return
            filter_status: Optional status filter ('open', 'in_progress', 'closed')
            filter_priority: Optional priority filter ('low', 'medium', 'high', 'urgent')

        Returns:
            List of matching tickets with relevance scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()

            # Build filter
            where_filter = {}
            if filter_status:
                where_filter['status'] = filter_status
            if filter_priority:
                where_filter['priority'] = filter_priority

            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter if where_filter else None
            )

            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, ticket_id in enumerate(results['ids'][0]):
                    # Calculate relevance score from distance
                    # With cosine similarity: distance ranges from 0 (identical) to 2 (opposite)
                    # Convert to percentage: 0 = 100% relevant, 2 = 0% relevant
                    distance = results['distances'][0][i] if 'distances' in results else 0

                    # Cosine distance to similarity: similarity = 1 - (distance / 2)
                    # Map to 0-1 scale
                    relevance_score = max(0, min(1, 1 - (distance / 2)))

                    formatted_results.append({
                        'ticket_id': ticket_id,
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': distance,
                        'relevance_score': relevance_score
                    })

            return formatted_results

        except Exception as e:
            print(f"Error searching tickets: {e}")
            return []

    def delete_ticket(self, ticket_id: str) -> bool:
        """
        Delete a ticket from the vector database

        Args:
            ticket_id: ID of the ticket to delete

        Returns:
            True if successful
        """
        try:
            self.collection.delete(ids=[str(ticket_id)])
            print(f"Deleted ticket #{ticket_id}")
            return True
        except Exception as e:
            print(f"Error deleting ticket: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the ticket collection

        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            return {
                'total_tickets': count,
                'collection_name': self.collection.name
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}