#!/usr/bin/env python3
"""
Standalone demo script to test RAG system without Django
This creates sample tickets and demonstrates search functionality
"""
from rag_service import TicketRAGService
from llm_service import MockLLMService
from datetime import datetime, timedelta
import random


def create_sample_tickets():
    """Create sample ticket data for testing"""
    sample_tickets = [
        {
            'id': 1,
            'title': 'Login page not loading',
            'ticket_description': 'Users are reporting that the login page shows a blank screen when accessed from Chrome browser. This started happening after the latest deployment.',
            'status': 'open',
            'priority': 'high',
            'created_date': datetime.now() - timedelta(days=2),
            'closed_date': None,
            'created_by': 'john.doe',
            'assigned_to': 'jane.smith',
            'cc_admins': ['admin1', 'admin2'],
            'cc_non_admins': ['user1']
        },
        {
            'id': 2,
            'title': 'Password reset emails not sending',
            'ticket_description': 'Multiple users have reported not receiving password reset emails. SMTP server logs show connection timeout errors.',
            'status': 'in_progress',
            'priority': 'urgent',
            'created_date': datetime.now() - timedelta(days=1),
            'closed_date': None,
            'created_by': 'sarah.johnson',
            'assigned_to': 'bob.wilson',
            'cc_admins': ['admin1'],
            'cc_non_admins': []
        },
        {
            'id': 3,
            'title': 'Dashboard loading slowly',
            'ticket_description': 'The main dashboard takes 30+ seconds to load. Database queries appear to be unoptimized. Affecting all users.',
            'status': 'open',
            'priority': 'medium',
            'created_date': datetime.now() - timedelta(days=5),
            'closed_date': None,
            'created_by': 'mike.brown',
            'assigned_to': 'alice.chen',
            'cc_admins': [],
            'cc_non_admins': ['user2', 'user3']
        },
        {
            'id': 4,
            'title': 'Export to CSV feature broken',
            'ticket_description': 'When users try to export reports to CSV, they receive a 500 error. Error logs show encoding issues with special characters.',
            'status': 'closed',
            'priority': 'low',
            'created_date': datetime.now() - timedelta(days=10),
            'closed_date': datetime.now() - timedelta(days=3),
            'created_by': 'lisa.anderson',
            'assigned_to': 'jane.smith',
            'cc_admins': ['admin2'],
            'cc_non_admins': []
        },
        {
            'id': 5,
            'title': 'Mobile app crashes on iOS 17',
            'ticket_description': 'Users on iOS 17 report that the mobile app crashes immediately after opening. Works fine on iOS 16 and Android.',
            'status': 'open',
            'priority': 'high',
            'created_date': datetime.now() - timedelta(hours=6),
            'closed_date': None,
            'created_by': 'tom.davis',
            'assigned_to': 'bob.wilson',
            'cc_admins': ['admin1', 'admin2'],
            'cc_non_admins': ['user1', 'user2']
        },
        {
            'id': 6,
            'title': 'API rate limiting too aggressive',
            'ticket_description': 'Partners are complaining that API rate limits are too strict. They are getting 429 errors even with normal usage patterns.',
            'status': 'in_progress',
            'priority': 'medium',
            'created_date': datetime.now() - timedelta(days=4),
            'closed_date': None,
            'created_by': 'emily.white',
            'assigned_to': 'alice.chen',
            'cc_admins': [],
            'cc_non_admins': ['user3']
        },
        {
            'id': 7,
            'title': 'Unable to upload large files',
            'ticket_description': 'Users cannot upload files larger than 50MB. System shows "Request Entity Too Large" error. Need to increase upload limit.',
            'status': 'closed',
            'priority': 'medium',
            'created_date': datetime.now() - timedelta(days=15),
            'closed_date': datetime.now() - timedelta(days=8),
            'created_by': 'chris.lee',
            'assigned_to': 'jane.smith',
            'cc_admins': ['admin2'],
            'cc_non_admins': []
        },
        {
            'id': 8,
            'title': 'Search functionality returns no results',
            'ticket_description': 'Global search feature is broken. Users enter queries but get zero results even for known existing content.',
            'status': 'open',
            'priority': 'urgent',
            'created_date': datetime.now() - timedelta(hours=12),
            'closed_date': None,
            'created_by': 'david.martinez',
            'assigned_to': 'Unassigned',
            'cc_admins': ['admin1'],
            'cc_non_admins': ['user1', 'user2']
        },
    ]
    
    return sample_tickets


def demo_search(rag_service, llm_service):
    """Demonstrate various search scenarios"""
    
    print("\n" + "="*70)
    print("RAG TICKET SEARCH DEMO")
    print("="*70)
    
    # Test queries
    queries = [
        "Show me all high priority tickets",
        "What issues are related to email?",
        "Are there any mobile app problems?",
        "Which tickets are assigned to jane.smith?",
        "What performance issues do we have?",
        "Show me urgent open tickets",
    ]
    
    for query in queries:
        print(f"\n{'─'*70}")
        print(f"Query: {query}")
        print(f"{'─'*70}")
        
        # Search
        results = rag_service.search_tickets(query, n_results=3)
        
        if not results:
            print("No results found.")
            continue
        
        # Show search results
        print(f"\nFound {len(results)} relevant tickets:\n")
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            score = result['relevance_score']
            print(f"{i}. Ticket #{metadata['ticket_id']}: {metadata['title']}")
            print(f"   Status: {metadata['status']} | Priority: {metadata['priority']} | Relevance: {score:.1%}")
            print(f"   Assigned to: {metadata['assigned_to']}")
        
        # Generate LLM answer
        print(f"\nAI Response:")
        print("-" * 70)
        answer = llm_service.generate_answer(query, results)
        print(answer)
    
    print(f"\n{'='*70}\n")


def main():
    """Main demo function"""
    print("Initializing RAG Ticket System Demo...")
    print("This demo uses local embeddings (sentence-transformers) and ChromaDB")
    print()
    
    # Initialize services
    print("Loading RAG service...")
    rag_service = TicketRAGService()
    
    print("Loading LLM service (Mock mode - no Ollama required)...")
    llm_service = MockLLMService()
    
    # Create and add sample tickets
    print("\nCreating sample tickets...")
    sample_tickets = create_sample_tickets()
    
    print(f"Adding {len(sample_tickets)} tickets to RAG system...")
    success_count = rag_service.add_tickets_bulk(sample_tickets)
    
    # Show stats
    stats = rag_service.get_collection_stats()
    print(f"\nSuccessfully added {success_count} tickets")
    print(f"Total tickets in database: {stats['total_tickets']}")
    
    # Run demo searches
    demo_search(rag_service, llm_service)
    
    print("\n" + "="*70)
    print("Demo completed!")
    print("\nTo use with real Ollama LLM:")
    print("1. Install Ollama: https://ollama.ai/download")
    print("2. Run: ollama run llama2")
    print("3. In code, use: LocalLLMService() instead of MockLLMService()")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
