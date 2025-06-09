"""Event bus interface for decoupling components."""

from abc import ABC, abstractmethod
from typing import Type, Callable, Any

# Events are just plain objects, no base class needed


class EventBus(ABC):
    """Interface for event bus implementations."""
    
    @abstractmethod
    async def publish(self, event: Any) -> None:
        """Emit an event to all subscribers."""
        pass
    
    @abstractmethod
    def subscribe(
        self, 
        event_type: Type[Any], 
        handler: Callable[[Any], None]
    ) -> None:
        """Subscribe to events of a specific type."""
        pass
    
    @abstractmethod
    def unsubscribe(
        self,
        event_type: Type[Any],
        handler: Callable[[Any], None]
    ) -> None:
        """Unsubscribe from events of a specific type."""
        pass