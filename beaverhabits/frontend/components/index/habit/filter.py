from typing import List
from nicegui import ui

from beaverhabits.sql.models import Habit

@ui.refreshable
async def letter_filter_ui(active_habits: List[Habit]):
    """Letter filter component for filtering habits by first letter."""
    # Get unique first letters
    available_letters = sorted(set(habit.name[0].upper() for habit in active_habits))
    
    with ui.row().classes("w-full justify-center gap-2 mb-2"):
        for letter in available_letters:
            ui.button(
                letter,
                on_click=lambda l=letter: ui.run_javascript(
                    f'window.HabitFilter.filterHabits("{l}");'
                )
            ).props('flat dense').classes('letter-filter-btn')

def should_show_filter(current_list_id: str | int | None, current_list: 'HabitList | None', global_setting: bool) -> bool:
    """Determine if letter filter should be shown based on context."""
    from beaverhabits.logging import logger
    
    # First check global setting
    if not global_setting:
        return False
    
    # Handle specific cases
    if current_list_id is None:
        # No list selected (showing all habits)
        return global_setting
    elif current_list_id == "None":
        # "No List" view (showing only habits without a list)
        return global_setting
    elif isinstance(current_list_id, int):
        # Specific list selected
        if current_list is None:
            # List not found or error fetching list details
            return False
        else:
            # Use list's setting
            return current_list.enable_letter_filter
    else:
        # Invalid list ID type
        return False
