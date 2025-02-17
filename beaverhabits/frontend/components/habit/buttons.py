from typing import Callable
from nicegui import ui, events

from beaverhabits.frontend import icons
from beaverhabits.logging import logger
from beaverhabits.storage.storage import Habit, HabitList, HabitStatus

class HabitEditButton(ui.button):
    def __init__(self, habit: Habit) -> None:
        super().__init__(on_click=self._async_task, icon="edit_square")
        self.habit = habit
        self.props("flat fab-mini color=grey-8")

    async def _async_task(self):
        pass

class HabitDeleteButton(ui.button):
    def __init__(self, habit: Habit, habit_list: HabitList, refresh: Callable) -> None:
        icon = icons.DELETE if habit.status == HabitStatus.ACTIVE else icons.DELETE_F
        super().__init__(on_click=self._async_task, icon=icon)
        self.habit = habit
        self.habit_list = habit_list
        self.refresh = refresh
        self.props("flat fab-mini color=grey-9")

        # Double confirm dialog to delete habit
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Are you sure to delete habit: {habit.name}?")
            with ui.row():
                ui.button("Yes", on_click=lambda: dialog.submit(True))
                ui.button("No", on_click=lambda: dialog.submit(False))
        self.dialog = dialog

    async def _async_task(self):
        if self.habit.status == HabitStatus.ACTIVE:
            self.habit.status = HabitStatus.ARCHIVED
            logger.info(f"Archive habit: {self.habit.name}")

        elif self.habit.status == HabitStatus.ARCHIVED:
            if not await self.dialog:
                return
            self.habit.status = HabitStatus.SOLF_DELETED
            logger.info(f"Soft delete habit: {self.habit.name}")

        self.refresh()

class HabitAddButton:
    def __init__(self, habit_list: HabitList, refresh: Callable, list_options: list[dict] = None) -> None:
        self.habit_list = habit_list
        self.refresh = refresh
        
        with ui.row().classes("w-full items-center gap-2"):
            self.name_input = ui.input("New habit name").props('dense outlined')
            self.name_input.classes("flex-grow")
            ui.button("Add Habit", on_click=self._async_task).props("unelevated")
            
        # Keep enter key functionality
        self.name_input.on("keydown.enter", self._async_task)

    async def _async_task(self):
        if not self.name_input.value:
            return
        await self.habit_list.add(self.name_input.value)
        logger.info(f"Added new habit: {self.name_input.value}")
        
        # Get the new habit's ID (it's the last one in the list)
        habits = self.habit_list.habits
        if habits:
            new_habit_id = habits[-1].id
            # Refresh the UI
            self.refresh()
            # Scroll to the new habit
            ui.run_javascript(f"""
            setTimeout(() => {{
                const cards = document.querySelectorAll(`[data-habit-id="{new_habit_id}"]`);
                const card = cards[cards.length - 1];  // Get the last matching card
                if (card) {{
                    // First scroll to make sure the card is in view
                    card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    
                    // Add highlight effect
                    card.classList.add('highlight-card');
                    setTimeout(() => {{
                        card.classList.remove('highlight-card');
                    }}, 1000);
                }}
            }}, 300);  // Increased delay to ensure DOM is updated
            """)
        else:
            self.refresh()
            
        self.name_input.set_value("")
