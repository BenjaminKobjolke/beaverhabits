import os
from contextlib import asynccontextmanager
from typing import List as TypeList

from nicegui import app, context, ui

from beaverhabits.app.crud import get_user_lists
from beaverhabits.app.auth import user_logout
from beaverhabits.configs import settings
from beaverhabits.frontend import icons, css
from beaverhabits.frontend.components import compat_menu, menu_header, menu_icon_button
from beaverhabits.logging import logger
from beaverhabits.sql.models import HabitList


def redirect(x):
    ui.navigate.to(os.path.join(settings.GUI_MOUNT_PATH, x))


def open_tab(x):
    ui.navigate.to(os.path.join(settings.GUI_MOUNT_PATH, x), new_tab=True)


def handle_list_change(e, name_to_id: dict, path: str):
    """Handle list selection change."""
    # Update storage
    app.storage.user.update({"current_list": name_to_id[e.value]})
    
    # Get list parameter
    list_param = name_to_id[e.value]
    
    # Determine target URL
    if path.endswith("/add"):
        # For add page
        target_url = f"{path}?list={list_param}" if list_param is not None else f"{path}?list=None"
    else:
        # For main page
        target_url = f"{settings.GUI_MOUNT_PATH}?list={list_param}" if list_param is not None else f"{settings.GUI_MOUNT_PATH}?list=None"
    
    logger.debug(f"List selector - navigating to: {target_url}")
    ui.navigate.to(target_url)


def add_page_scripts():
    """Add JavaScript and CSS to the page."""
    # Add settings as JavaScript variables
    ui.add_head_html(f'''
        <script>
        window.HABIT_SETTINGS = {{
            colors: {{
                skipped: "{settings.HABIT_COLOR_SKIPPED}",
                completed: "{settings.HABIT_COLOR_COMPLETED}",
                incomplete: "{settings.HABIT_COLOR_INCOMPLETE}",
                last_week_incomplete: "{settings.HABIT_COLOR_LAST_WEEK_INCOMPLETE}"
            }}
        }};
        </script>
    ''')
    
    # Add JavaScript files
    from beaverhabits.frontend.javascript import js_paths
    for js_file in js_paths.values():
        ui.add_head_html(f'<script src="{js_file}"></script>')
    
    # Add habit filter script
    ui.add_head_html('<script src="/statics/js/habit-filter.js"></script>')
    
    # Add CSS for animations
    ui.add_head_html(f'<style>{css.habit_animations}</style>')
    # Add CSS for transitions
    ui.add_head_html('''
        <style>
        .habit-card {
            transition: transform 0.3s ease-out;
        }
        .resort-pending {
            position: relative;
        }
        .resort-pending::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 2px;
            background: #4CAF50;
            animation: progress 2s linear;
        }
        @keyframes progress {
            0% { width: 100%; }
            100% { width: 0%; }
        }
        .highlight-card {
            animation: highlight 1s ease-out;
        }
        @keyframes highlight {
            0% { background-color: rgba(76, 175, 80, 0.2); }
            100% { background-color: transparent; }
        }
        </style>
    ''')

def custom_header():
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
    )
    ui.add_head_html('<meta name="apple-mobile-web-app-title" content="Beaver">')
    ui.add_head_html(
        '<meta name="apple-mobile-web-app-status-bar-style" content="black">'
    )
    ui.add_head_html('<meta name="theme-color" content="#121212">')

    # viewBox="90 90 220 220"
    ui.add_head_html(
        '<link rel="apple-touch-icon" href="/statics/images/apple-touch-icon-v4.png">'
    )

    # Experimental PWA support
    if settings.ENABLE_IOS_STANDALONE:
        ui.add_head_html('<meta name="apple-mobile-web-app-capable" content="yes">')


def add_umami_headers():
    ui.add_head_html(
        '<script defer src="https://cloud.umami.is/script.js" data-website-id="246fa4ac-0f4f-464a-8a32-14c9f75fed77"></script>'
    )


@ui.refreshable
async def list_selector(lists: TypeList[HabitList], current_list_id: int | None = None, path: str = ""):
    """Dropdown for selecting current list."""
    with ui.row().classes("items-center gap-2"):
        # Dropdown for list selection
        # Create name-to-id mapping
        name_to_id = {"No List": None}
        name_to_id.update({list.name: list.id for list in lists if not list.deleted})
        
        # Create options list
        options = list(name_to_id.keys())
        
        # Get current list ID from URL
        try:
            current_list_param = current_list_id if current_list_id is not None else ""
            logger.debug(f"List selector - current_list_param: {current_list_param}")
            
            # Handle different list parameter cases
            if current_list_param == "None":
                current_name = "No List"
                logger.debug("List selector - using 'No List'")
            elif current_list_param.isdigit():
                list_id = int(current_list_param)
                current_name = next(
                    (name for name, id in name_to_id.items() if id == list_id),
                    "No List"
                )
                logger.debug(f"List selector - found name: {current_name} for ID: {list_id}")
            else:
                current_name = "No List"
                logger.debug("List selector - defaulting to 'No List'")
        except (AttributeError, ValueError) as e:
            logger.error(f"List selector - error parsing list ID: {e}")
            current_name = "No List"
        
        # Log debug info
        logger.debug(f"List options: {options}")
        logger.debug(f"Current list ID: {current_list_id}")
        logger.debug(f"Current name: {current_name}")
        
        ui.select(
            options=options,
            value=current_name,
            on_change=lambda e: handle_list_change(e, name_to_id, path)
        ).props('outlined dense options-dense')


def menu_component() -> None:
    """Dropdown menu for the top-right corner of the page."""
    with ui.menu():
        show_import = True
        show_export = True

        path = context.client.page.path
        if "add" in path:
            compat_menu("Reorder", lambda: redirect("order"))
        else:
            compat_menu("Configure habits", lambda: redirect("add"))
        ui.separator()

        compat_menu("Configure lists", lambda: redirect("lists"))
        ui.separator()

        if show_export:
            compat_menu("Export", lambda: open_tab("export"))
            ui.separator()
        if show_import:
            compat_menu("Import", lambda: redirect("import"))
            ui.separator()

        compat_menu("Logout", lambda: user_logout() and ui.navigate.to("/login"))


@asynccontextmanager
async def layout(title: str | None = None, with_menu: bool = True, user=None):
    """Base layout for all pages."""

    title = title or "Beaver Habits"

    with ui.column().classes("w-full") as c:

        # Standard headers and scripts
        custom_header()
        add_umami_headers()
        add_page_scripts()

        path = context.client.page.path
        logger.info(f"Rendering page: {path}")
        with ui.row().classes("w-full items-center justify-between p-4"):
            # Show title on all pages except main /gui page
            if path != settings.GUI_MOUNT_PATH:
                # Get page-specific title
                page_title = (
                    "Add Habit" if "/add" in path
                    else "Configure Lists" if "/lists" in path
                    else "Reorder Habits" if "/order" in path
                    else "Import" if "/import" in path
                    else "Export" if "/export" in path
                    else "Habit Details" if "/habits/" in path
                    else title
                )
                menu_header(page_title, target=settings.GUI_MOUNT_PATH)
            
            # Add list selector if not on lists, add, or order pages
            if not any(x in path for x in ["/lists", "/add", "/order"]) and user:
                lists = await get_user_lists(user)
                # Get current list from URL parameter
                try:
                    current_list = context.client.page.query.get("list", "") if hasattr(context.client.page, "query") else ""
                    logger.debug(f"Layout - current list from URL: {current_list}")
                except Exception as e:
                    logger.debug(f"Layout - error getting list from URL: {e}")
                    current_list = ""
                await list_selector(lists, current_list, path)
            else:
                ui.space()  # Empty space on the left when no list selector
                
            if with_menu:
                with menu_icon_button(icons.MENU):
                    menu_component()

        yield
