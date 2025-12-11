"""
Django signals to automatically update RAG when tickets are created/updated/deleted
Add this to your tickets/signals.py
"""
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from tickets.models import Ticket
from tickets.rag_service import TicketRAGService
import logging

logger = logging.getLogger(__name__)

# Initialize RAG service (singleton pattern)
_rag_service = None

def get_rag_service():
    global _rag_service
    if _rag_service is None:
        _rag_service = TicketRAGService()
    return _rag_service


@receiver(post_save, sender=Ticket)
def sync_ticket_to_rag(sender, instance, created, **kwargs):
    """
    Automatically sync ticket to RAG when created or updated
    """
    try:
        rag_service = get_rag_service()
        
        ticket_data = {
            'id': instance.id,
            'title': instance.title,
            'ticket_description': instance.ticket_description,
            'status': instance.status,
            'priority': instance.priority,
            'created_date': instance.created_date,
            'closed_date': instance.closed_date,
            'created_by': instance.created_by.username,
            'assigned_to': instance.assigned_to.username if instance.assigned_to else 'Unassigned',
            'cc_admins': [u.username for u in instance.cc_admins.all()],
            'cc_non_admins': [u.username for u in instance.cc_non_admins.all()],
        }
        
        rag_service.add_ticket(ticket_data)
        action = "Created" if created else "Updated"
        logger.info(f"{action} ticket #{instance.id} in RAG")
        
    except Exception as e:
        logger.error(f"Error syncing ticket #{instance.id} to RAG: {e}")


@receiver(post_delete, sender=Ticket)
def delete_ticket_from_rag(sender, instance, **kwargs):
    """
    Automatically remove ticket from RAG when deleted
    """
    try:
        rag_service = get_rag_service()
        rag_service.delete_ticket(str(instance.id))
        logger.info(f"Deleted ticket #{instance.id} from RAG")
        
    except Exception as e:
        logger.error(f"Error deleting ticket #{instance.id} from RAG: {e}")


@receiver(m2m_changed, sender=Ticket.cc_admins.through)
@receiver(m2m_changed, sender=Ticket.cc_non_admins.through)
def sync_ticket_cc_changes(sender, instance, action, **kwargs):
    """
    Sync ticket when CC lists are updated
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        try:
            # Re-sync the entire ticket
            sync_ticket_to_rag(Ticket, instance, created=False)
        except Exception as e:
            logger.error(f"Error syncing CC changes for ticket #{instance.id}: {e}")
