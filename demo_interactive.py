#!/usr/bin/env python3
"""
Interactive RAG Demo with Streaming - Ask your own questions!
"""
from rag_service import TicketRAGService
from llm_service import MockLLMService, LocalLLMService
from datetime import datetime, timedelta
import sys


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


def display_results(query, results, llm_service):
    """Display search results with streaming AI response"""
    print(f"\n{'─' * 70}")
    print(f"Query: {query}")
    print(f"{'─' * 70}")

    if not results:
        print("No results found.")
        return

    # Show search results
    print(f"\nFound {len(results)} relevant ticket(s):\n")
    for i, result in enumerate(results, 1):
        metadata = result['metadata']
        score = result['relevance_score']
        print(f"{i}. Ticket #{metadata['ticket_id']}: {metadata['title']}")
        print(f"   Status: {metadata['status']} | Priority: {metadata['priority']} | Relevance: {score:.1%}")
        print(f"   Assigned to: {metadata['assigned_to']}")
        print()

    # Generate LLM answer with streaming
    print(f"AI Response:")
    print("-" * 70)

    # Check if we're using MockLLMService (doesn't support streaming)
    if isinstance(llm_service, MockLLMService):
        answer = llm_service.generate_answer(query, results)
        print(answer)
    else:
        # Stream the response token by token
        response_generator = llm_service.generate_answer(query, results, stream=True)

        # If it's a string (error case), just print it
        if isinstance(response_generator, str):
            print(response_generator)
        else:
            # Stream and print each chunk as it arrives
            try:
                for chunk in response_generator:
                    print(chunk, end='', flush=True)
                print()  # Newline after streaming complete
            except Exception as e:
                print(f"\nStreaming error: {e}")


def show_help():
    """Show available commands and example queries"""
    print("\n" + "=" * 70)
    print("HELP - Available Commands & Example Queries")
    print("=" * 70)
    print("\nCommands:")
    print("  help  - Show this help message")
    print("  list  - List all tickets in the database")
    print("  stats - Show database statistics")
    print("  exit  - Exit the interactive demo")
    print("  quit  - Exit the interactive demo")
    print("\nExample Queries:")
    print("  - Show me all high priority tickets")
    print("  - What issues are related to email?")
    print("  - Are there any mobile app problems?")
    print("  - Which tickets are assigned to jane.smith?")
    print("  - What performance issues do we have?")
    print("  - Show me urgent open tickets")
    print("  - Find tickets about login")
    print("  - What's broken in the system?")
    print("  - Show closed tickets")
    print("  - API related issues")
    print("=" * 70 + "\n")


def list_all_tickets(rag_service):
    """Display all tickets in the database"""
    print("\n" + "=" * 70)
    print("ALL TICKETS IN DATABASE")
    print("=" * 70 + "\n")

    # Get all tickets by searching with empty query
    results = rag_service.search_tickets("", n_results=20)

    if not results:
        print("No tickets found in database.")
        return

    for i, result in enumerate(results, 1):
        metadata = result['metadata']
        print(f"{i}. Ticket #{metadata['ticket_id']}: {metadata['title']}")
        print(f"   Status: {metadata['status']} | Priority: {metadata['priority']}")
        print(f"   Assigned to: {metadata['assigned_to']}")
        print()


def show_stats(rag_service):
    """Show database statistics"""
    stats = rag_service.get_collection_stats()
    print(f"\nDatabase Statistics:")
    print(f"  Total tickets indexed: {stats['total_tickets']}")
    print(f"  Collection name: {stats['collection_name']}\n")


def interactive_search(rag_service, llm_service):
    """Interactive search loop"""
    print("\n" + "=" * 70)
    print("INTERACTIVE RAG SEARCH (WITH STREAMING)")
    print("=" * 70)
    print("\nType your question and press Enter to search.")
    print("Type 'help' for commands and examples, 'exit' to quit.\n")

    while True:
        try:
            # Get user input
            query = input("Your question: ").strip()

            # Handle empty input
            if not query:
                continue

            # Handle commands
            if query.lower() in ['exit', 'quit']:
                print("\nThanks for trying the RAG demo! Goodbye!\n")
                break

            elif query.lower() == 'help':
                show_help()
                continue

            elif query.lower() == 'list':
                list_all_tickets(rag_service)
                continue

            elif query.lower() == 'stats':
                show_stats(rag_service)
                continue

            # Parse query for filters
            filter_status = None
            filter_priority = None
            check_unassigned = False

            # Detect status filters
            query_lower = query.lower()
            if 'open' in query_lower and 'status' in query_lower:
                filter_status = 'open'
            elif 'closed' in query_lower:
                filter_status = 'closed'
            elif 'in progress' in query_lower or 'in_progress' in query_lower:
                filter_status = 'in_progress'

            # Detect priority filters
            if 'urgent' in query_lower:
                filter_priority = 'urgent'
            elif 'high priority' in query_lower or 'high' in query_lower:
                filter_priority = 'high'
            elif 'medium priority' in query_lower or 'medium' in query_lower:
                filter_priority = 'medium'
            elif 'low priority' in query_lower or 'low' in query_lower:
                filter_priority = 'low'

            # Detect unassigned filter
            if 'unassigned' in query_lower:
                check_unassigned = True

            # Perform search
            results = rag_service.search_tickets(
                query,
                n_results=10 if check_unassigned else 5,
                filter_status=filter_status,
                filter_priority=filter_priority
            )

            # Post-filter for unassigned tickets if needed
            if check_unassigned:
                results = [r for r in results if r['metadata'].get('assigned_to') == 'Unassigned'][:5]
                if results:
                    print(f"\nFiltered to show only unassigned tickets")

            # Show active filters
            if filter_status or filter_priority:
                filters_applied = []
                if filter_status:
                    filters_applied.append(f"status={filter_status}")
                if filter_priority:
                    filters_applied.append(f"priority={filter_priority}")
                print(f"\nFilters applied: {', '.join(filters_applied)}")

            if not results:
                print(f"\nNo tickets found matching your query.")
                if check_unassigned:
                    print("  Tip: There might not be any unassigned tickets in the database.")
                print()
                continue

            display_results(query, results, llm_service)

            print()  # Extra line for spacing

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def main():
    """Main interactive demo function"""
    print("=" * 70)
    print("INTERACTIVE RAG TICKET SEARCH DEMO (WITH STREAMING)")
    print("=" * 70)
    print("\nInitializing...")

    # Initialize services
    print("Loading RAG service...")
    rag_service = TicketRAGService()

    # Try to use Ollama, fall back to Mock if not available
    print("Checking for Ollama...")
    llm_service = LocalLLMService(model="llama3.2:3b")

    if llm_service.check_ollama_running():
        print("Ollama is running! Using llama3.2:3b with streaming enabled.")
    else:
        print("Ollama not detected. Using Mock service instead.")
        print("  To use AI: Install Ollama and run 'ollama serve'")
        llm_service = MockLLMService()

    # Check if database exists
    stats = rag_service.get_collection_stats()

    if stats['total_tickets'] == 0:
        print("\nNo tickets found. Loading sample data...")
        sample_tickets = create_sample_tickets()
        success_count = rag_service.add_tickets_bulk(sample_tickets)
        print(f"Added {success_count} sample tickets")
    else:
        print(f"Found {stats['total_tickets']} existing tickets")

    # Start interactive search
    interactive_search(rag_service, llm_service)

    print("=" * 70)
    print("Demo completed!")
    print("\nTips:")
    print("  - Try different phrasings of the same question")
    print("  - Search by status, priority, assignee, or topic")
    print("  - The system understands semantic meaning, not just keywords")
    print("  - AI responses stream in real-time for faster perceived speed")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()