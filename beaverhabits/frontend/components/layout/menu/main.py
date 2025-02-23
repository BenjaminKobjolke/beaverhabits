from nicegui import ui, context

from beaverhabits.app.auth import user_logout
from beaverhabits.frontend.components import compat_menu
from beaverhabits.frontend.components.layout.utils.navigation import redirect, open_tab

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
