"""
Django views for RAG-powered ticket search
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from tickets.rag_service import TicketRAGService
from tickets.llm_service import LocalLLMService, MockLLMService
import json


@method_decorator(login_required, name='dispatch')
class TicketSearchRAGView(View):
    """
    View for RAG-powered natural language ticket search
    """
    
    def get(self, request):
        """Render the search interface"""
        return render(request, 'tickets/rag_search.html')
    
    def post(self, request):
        """Handle search queries"""
        try:
            # Parse request
            data = json.loads(request.body)
            query = data.get('query', '')
            n_results = data.get('n_results', 5)
            filter_status = data.get('filter_status')
            filter_priority = data.get('filter_priority')
            use_llm = data.get('use_llm', False)  # Whether to use LLM for generation
            
            if not query:
                return JsonResponse({'error': 'Query is required'}, status=400)
            
            # Initialize services
            rag_service = TicketRAGService()
            
            # Search for relevant tickets
            results = rag_service.search_tickets(
                query=query,
                n_results=n_results,
                filter_status=filter_status,
                filter_priority=filter_priority
            )
            
            # Prepare response
            response_data = {
                'query': query,
                'results': results,
                'total_found': len(results)
            }
            
            # Optionally generate answer using LLM
            if use_llm and results:
                try:
                    llm_service = MockLLMService()  # Use mock by default
                    # llm_service = LocalLLMService()  # Uncomment if Ollama is running
                    
                    answer = llm_service.generate_answer(query, results)
                    response_data['generated_answer'] = answer
                except Exception as e:
                    response_data['llm_error'] = str(e)
            
            return JsonResponse(response_data)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class TicketRAGStatsView(View):
    """
    View to get RAG system statistics
    """
    
    def get(self, request):
        try:
            rag_service = TicketRAGService()
            stats = rag_service.get_collection_stats()
            return JsonResponse(stats)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
