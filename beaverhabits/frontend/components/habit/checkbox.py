import asyncio
import datetime
from typing import Callable

from nicegui import ui, events

from beaverhabits.configs import settings
from beaverhabits.frontend import icons
from beaverhabits.logging import logger
from beaverhabits.storage.storage import CheckedRecord, Habit, get_week_ticks, get_last_week_completion
from ..utils import ratelimiter

DAILY_NOTE_MAX_LENGTH = 300

def habit_tick_dialog(record: CheckedRecord | None):
    text = record.text if record else ""
    with ui.dialog() as dialog, ui.card().props("flat") as card:
        dialog.props('backdrop-filter="blur(4px)"')
        card.classes("w-5/6 max-w-80")

        with ui.column().classes("gap-0 w-full"):
            t = ui.textarea(
                label="Note",
                value=text,
                validation={
                    "Too long!": lambda value: len(value) < DAILY_NOTE_MAX_LENGTH
                },
            )
            t.classes("w-full")

            with ui.row():
                ui.button("Yes", on_click=lambda: dialog.submit((True, t.value))).props(
                    "flat"
                )
                ui.button("No", on_click=lambda: dialog.submit((False, t.value))).props(
                    "flat"
                )
    return dialog

async def note_tick(habit: Habit, day: datetime.date) -> bool | None:
    record = habit.record_by(day)
    result = await habit_tick_dialog(record)

    if result is None:
        return

    yes, text = result
    if text and len(text) > DAILY_NOTE_MAX_LENGTH:
        ui.notify("Note is too long", color="negative")
        return

    record = await habit.tick(day, yes, text)
    
    # Scroll to the updated habit
    ui.run_javascript(f"scrollToHabit('{habit.id}')")
    
    return record.done

@ratelimiter(limit=30, window=30)
@ratelimiter(limit=10, window=1)
async def habit_tick(habit: Habit, day: datetime.date, value: bool | None):
    # Avoid duplicate tick
    record = habit.record_by(day)
    
    if record and record.done is value:  # Use 'is' to handle None case correctly
        return

    # Transaction start
    await habit.tick(day, value)
    
    # Scroll to the updated habit
    ui.run_javascript(f"""
    setTimeout(() => {{
        const cards = document.querySelectorAll(`[data-habit-id="{habit.id}"]`);
        const card = cards[cards.length - 1];
        if (card) {{
            card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            
            // Add highlight effect
            card.classList.add('highlight-card');
            setTimeout(() => {{
                card.classList.remove('highlight-card');
            }}, 1000);
        }}
    }}, 300);  // Delay to ensure DOM is updated
    """)

class BaseHabitCheckBox(ui.checkbox):
    def __init__(self, habit: Habit, day: datetime.date, value: bool | None) -> None:
        # Initialize with the actual state
        super().__init__("", value=value if value is not None else False)
        self.habit = habit
        self.day = day
        self.skipped = value is None  # Track skipped state
        text_color = "chartreuse" if self.day == datetime.date.today() else settings.HABIT_COLOR_DAY_NUMBER
        self.unchecked_icon = icons.SQUARE.format(color="rgb(54,54,54)", text=self.day.day, text_color=text_color)
        self.checked_icon = icons.DONE
        self.skipped_icon = icons.CLOSE
        
        # Set up initial state
        self._update_icons()
        self._update_style(value)

        # Hold on event flag
        self.hold = asyncio.Event()
        self.moving = False

    def _update_icons(self):
        if self.skipped:
            self.props(f'checked-icon="{self.skipped_icon}" unchecked-icon="{self.skipped_icon}" keep-color')
        elif self.value:
            self.props(f'checked-icon="{self.checked_icon}" unchecked-icon="{self.checked_icon}" keep-color')
        else:
            self.props(f'checked-icon="{self.unchecked_icon}" unchecked-icon="{self.unchecked_icon}" keep-color')

    async def _update_style(self, value: bool | None):
        # First update internal state
        if value is None:  # Skipped state
            self.value = True  # Show skipped icon
            self.skipped = True
        else:
            self.value = value
            self.skipped = False
        
        # Then update visual state
        if self.skipped:
            self.props("color=grey-8")
        else:
            self.props("color=currentColor" if self.value else "color=grey-8")
        
        self._update_icons()
            
        # Add a small delay to ensure habit state is updated
        await asyncio.sleep(0.1)
            
        # Get fresh ticked days after state update
        ticked_days = set(self.habit.ticked_days)
        if value:  # Add current day if it's being checked
            ticked_days.add(self.day)
        elif value is False:  # Remove current day if it's being unchecked
            ticked_days.discard(self.day)
            
        # Get ticks for current week and last week's completion status
        week_ticks, _ = get_week_ticks(self.habit, self.day)
        last_week_complete = get_last_week_completion(self.habit, self.day)
        
        # Check if this habit is skipped today
        is_skipped_today = (
            self.day == datetime.date.today() and 
            self.habit.record_by(self.day) and 
            self.habit.record_by(self.day).done is None
        )
        
        # Update state directly without refreshing
        ui.run_javascript(f"updateHabitAttributes('{self.habit.id}', {self.habit.weekly_goal or 0}, {week_ticks}, {str(is_skipped_today).lower() if is_skipped_today is not None else 'null'}, {str(last_week_complete).lower()})")

    async def _mouse_down_event(self, e):
        self.hold.clear()
        self.moving = False
        try:
            async with asyncio.timeout(0.2):
                await self.hold.wait()
        except asyncio.TimeoutError:
            if settings.ENABLE_HABIT_NOTES:
                value = await note_tick(self.habit, self.day)
                if value is not None:
                    await self._update_style(value)
            else:
                # Skip note dialog, just toggle to checked state
                value = True
                await habit_tick(self.habit, self.day, value)
                await self._update_style(value)
        else:
            if self.moving:
                return
            # Get current state from database
            record = self.habit.record_by(self.day)
            current_state = record.done if record else False
            
            # Determine next state based on current database state
            if current_state is None:  # Currently skipped
                value = False  # Move to original state
            elif current_state:  # Currently checked
                value = None  # Move to skipped
            else:  # Currently unchecked
                value = True  # Move to checked
            
            # Do update completion status
            await habit_tick(self.habit, self.day, value)
            # Update local state with latest data
            await self._update_style(value)

    async def _mouse_up_event(self, e):
        self.hold.set()

    async def _mouse_move_event(self):
        self.moving = True
        self.hold.set()

class HabitCheckBox(BaseHabitCheckBox):
    def __init__(self, habit: Habit, day: datetime.date, value: bool | None, refresh: Callable | None = None) -> None:
        super().__init__(habit, day, value)
        self.refresh = refresh

        # Event handlers
        self.on("mousedown", self._mouse_down_event)
        self.on("touchstart", self._mouse_down_event)
        self.on("mouseup.prevent", self._mouse_up_event)
        self.on("touchend.prevent", self._mouse_up_event)
        self.on("touchmove", self._mouse_move_event)

class HabitStarCheckbox(ui.checkbox):
    def __init__(self, habit: Habit, refresh: Callable) -> None:
        super().__init__("", value=habit.star)
        self.habit = habit
        self.refresh = refresh
        self.props("dense fab-mini color=yellow-8")
        self.props('checked-icon="star" unchecked-icon="star_outline" size="sm"')
        self.on("change", self._async_task)

    async def _async_task(self, e):
        self.habit.star = e.value
        
        self.refresh()
        
        # Scroll to the updated habit
        ui.run_javascript(f"scrollToHabit('{self.habit.id}')")

class CalendarCheckBox(BaseHabitCheckBox):
    def __init__(
        self,
        habit: Habit,
        day: datetime.date,
        today: datetime.date,
        is_bind_data: bool = True,
    ) -> None:
        # Get initial state before calling super()
        record = habit.record_by(day)
        initial_value = record.done if record else False
        
        # Pass the correct initial value to super()
        super().__init__(habit, day, initial_value)
        self.today = today
        
        self.classes("inline-block w-14")  # w-14 = width: 56px
        self.props("dense")
        
        # Event handlers
        self.on("mousedown", self._mouse_down_event)
        self.on("touchstart", self._mouse_down_event)
        self.on("mouseup.prevent", self._mouse_up_event)
        self.on("touchend.prevent", self._mouse_up_event)
        self.on("touchmove", self._mouse_move_event)
        self.on("click.prevent", lambda _: None)  # Prevent default click behavior
        self.on("change.prevent", lambda _: None)  # Prevent default change behavior
