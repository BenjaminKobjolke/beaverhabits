from nicegui import ui

from beaverhabits.configs import settings
from beaverhabits.frontend import css

def add_settings_script() -> None:
    """Add settings as JavaScript variables."""
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

def add_javascript_files() -> None:
    """Add JavaScript files to the page."""
    # Add utils first as other scripts may depend on it
    ui.add_head_html('<script src="/statics/js/utils.js"></script>')
    
    # Add settings before other scripts that use it
    ui.add_head_html('<script src="/statics/js/settings.js"></script>')
    
    # Add core habit scripts in dependency order
    ui.add_head_html('<script src="/statics/js/habit-color.js"></script>')
    ui.add_head_html('<script src="/statics/js/habit-sort.js"></script>')
    ui.add_head_html('<script src="/statics/js/habit-ui.js"></script>')
    ui.add_head_html('<script src="/statics/js/habit-progress.js"></script>')
    
    # Add filter script last as it depends on other scripts
    ui.add_head_html('<script src="/statics/js/habit-filter.js"></script>')
    
    # Add connection status monitoring script
    ui.add_head_html('''
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Create connection status banner if it doesn't exist
        if (!document.getElementById('connection-status-banner')) {
            const banner = document.createElement('div');
            banner.id = 'connection-status-banner';
            banner.textContent = 'Connection lost. Waiting to reconnect...';
            document.body.appendChild(banner);
        }
        
        // Variables to track connection state
        let isConnected = true;
        const connectionBanner = document.getElementById('connection-status-banner');
        
        // Function to show the connection lost banner
        function showConnectionLost() {
            if (connectionBanner) {
                connectionBanner.style.display = 'block';
            }
        }
        
        // Function to hide the connection lost banner
        function hideConnectionLost() {
            if (connectionBanner) {
                connectionBanner.style.display = 'none';
            }
        }
        
        // Monitor socket.io connection events
        const socketMonitorInterval = setInterval(function() {
            // Check if socket.io is loaded
            if (window._nicegui && window._nicegui.socket) {
                clearInterval(socketMonitorInterval);
                
                const socket = window._nicegui.socket;
                
                // Listen for disconnect events
                socket.on('disconnect', function() {
                    console.log('Socket disconnected');
                    isConnected = false;
                    showConnectionLost();
                });
                
                // Listen for reconnect events
                socket.on('connect', function() {
                    console.log('Socket connected');
                    isConnected = true;
                    hideConnectionLost();
                    
                    // Reload the page to ensure all data is fresh
                    // Only reload if we were previously disconnected to avoid unnecessary reloads
                    if (connectionBanner && connectionBanner.style.display === 'block') {
                        setTimeout(function() {
                            window.location.reload();
                        }, 1000);
                    }
                });
            }
        }, 100);
        
        // Add a fallback detection method using fetch API
        // This helps detect network issues even if socket.io doesn't report them
        setInterval(function() {
            if (!isConnected) {
                return; // Already know we're disconnected
            }
            
            // Try to fetch a small resource to check connection
            fetch(window.location.origin + '/health', {
                method: 'GET',
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache'
                }
            })
            .then(response => {
                if (response.ok) {
                    // Connection is working
                    if (!isConnected) {
                        console.log('Network connection restored');
                        // Don't set isConnected=true here, let socket.io handle that
                    }
                } else {
                    console.log('Network check failed with status:', response.status);
                    showConnectionLost();
                }
            })
            .catch(error => {
                console.log('Network check failed:', error);
                showConnectionLost();
            });
        }, 15000); // Check every 15 seconds
    });
    </script>
    ''')

def add_css_styles() -> None:
    """Add CSS styles to the page."""
    # Add root CSS to override NiceGUI defaults
    ui.add_head_html(f'<style>{css.ROOT_CSS}</style>')
    
    # Add CSS for animations
    ui.add_head_html(f'<style>{css.habit_animations}</style>')
    
    # Add CSS for connection status indicator
    ui.add_head_html('''
        <style>
        #connection-status-banner {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 9999;
            background-color: #e53935;
            color: white;
            text-align: center;
            padding: 10px;
            font-weight: bold;
            display: none;
        }
        </style>
    ''')
    
    # Add CSS for transitions
    ui.add_head_html('''
        <style>
        .habit-card {
            transition: transform 0.3s ease-out;
            position: relative;
            overflow: hidden;
        }
        .resort-pending {
            position: relative;
        }
        .progress-bar {
            position: absolute;
            bottom: 0;
            left: 0;
            height: 2px;
            width: 100%;
            background: #4CAF50;
            transform-origin: right;
            animation: progress-right-to-left 3s linear forwards;
        }
        
        @keyframes progress-right-to-left {
            from { transform: scaleX(1); }
            to { transform: scaleX(0); }
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

def add_all_scripts() -> None:
    """Add all scripts and styles to the page."""
    add_settings_script()
    add_javascript_files()
    add_css_styles()
