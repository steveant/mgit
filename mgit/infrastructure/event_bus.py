"""Simple in-memory event bus implementation."""

import asyncio
from collections import defaultdict
from typing import Type, Callable, Dict, List, Any, Union

from mgit.application.ports import EventBus


class InMemoryEventBus(EventBus):
    """Simple synchronous in-memory event bus."""
    
    def __init__(self):
        self._handlers: Dict[Union[Type[Any], str], List[Callable]] = defaultdict(list)
    
    async def publish(self, event: Any) -> None:
        """Publish an event to all subscribers."""
        # Support both type-based and string-based subscriptions
        event_type = type(event)
        event_name = event_type.__name__
        
        # Get handlers for both the type and the name
        handlers = list(self._handlers.get(event_type, []))
        handlers.extend(self._handlers.get(event_name, []))
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                # Log error but don't stop other handlers
                # In production, this would use proper logging
                print(f"Error in event handler: {e}")
    
    def subscribe(
        self,
        event_type: Union[Type[Any], str],
        handler: Callable[[Any], None]
    ) -> None:
        """Subscribe to events of a specific type or name."""
        self._handlers[event_type].append(handler)
    
    def unsubscribe(
        self,
        event_type: Union[Type[Any], str],
        handler: Callable[[Any], None]
    ) -> None:
        """Unsubscribe from events of a specific type or name."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                # Handler not in list
                pass