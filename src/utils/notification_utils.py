from PyQt5 import QtWidgets, QtCore, QtGui
import sys
import platform
import logging

# Configure a logger for this module
logger = logging.getLogger("ProductivityTracker.notifications")


def show_notification(title, message, icon_type=QtWidgets.QSystemTrayIcon.Information, duration=5000):
    """
    Show a system notification.

    This function attempts to show a notification using the system tray.
    If a system tray already exists in the app, it will use that.
    Otherwise, it creates a temporary one.

    Args:
        title (str): Notification title
        message (str): Notification message
        icon_type (QSystemTrayIcon.MessageIcon): Icon type to show
        duration (int): Duration in milliseconds to show the message

    Returns:
        bool: True if notification was shown, False otherwise
    """
    # Check if system supports notifications
    if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
        logger.warning("System tray not available, cannot show notification")
        return False

    # If we have access to system notifications
    try:
        # Get application instance
        app = QtWidgets.QApplication.instance()
        if app is None:
            # If there's no QApplication instance yet, we can't show notifications
            logger.warning("No QApplication instance, cannot show notification")
            return False

        # Try to find an existing system tray icon in the app
        main_window = app.activeWindow()
        if main_window and hasattr(main_window, 'system_tray'):
            # Use the application's existing system tray icon
            main_window.system_tray.show_message(title, message, icon_type, duration)
            return True

        # Create system tray icon if needed (temporary one if no existing)
        if not hasattr(show_notification, 'tray_icon'):
            show_notification.tray_icon = QtWidgets.QSystemTrayIcon()

            # Set an appropriate icon
            if hasattr(main_window, 'windowIcon') and not main_window.windowIcon().isNull():
                show_notification.tray_icon.setIcon(main_window.windowIcon())
            else:
                # Use a standard icon if no application icon is available
                icon = QtGui.QIcon.fromTheme("dialog-information")
                if icon.isNull():
                    # Fallback icon
                    icon = QtWidgets.QStyle.standardIcon(
                        QtWidgets.QApplication.style(),
                        QtWidgets.QStyle.SP_MessageBoxInformation
                    )
                show_notification.tray_icon.setIcon(icon)

        # Show notification
        show_notification.tray_icon.show()
        show_notification.tray_icon.showMessage(
            title, message, icon_type, duration
        )
        return True

    except Exception as e:
        logger.error(f"Could not show notification: {e}")
        return False


def show_platform_notification(title, message):
    """
    Show a notification using platform-specific methods.
    Useful as a fallback when Qt system tray notifications aren't available.

    Args:
        title (str): Notification title
        message (str): Notification message

    Returns:
        bool: True if notification was shown, False otherwise
    """
    try:
        system = platform.system()

        if system == "Windows":
            # Use Windows toast notifications (requires win10toast package)
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=5, threaded=True)
                return True
            except ImportError:
                logger.warning("win10toast package not installed, falling back to system tray")
                return show_notification(title, message)

        elif system == "Darwin":  # macOS
            # Use macOS notifications (requires terminal-notifier)
            import subprocess
            try:
                subprocess.Popen([
                    'terminal-notifier',
                    '-title', title,
                    '-message', message,
                    '-sound', 'default'
                ])
                return True
            except (FileNotFoundError, subprocess.SubprocessError):
                logger.warning("terminal-notifier not installed, falling back to system tray")
                return show_notification(title, message)

        elif system == "Linux":
            # Use Linux notifications (requires notify-send)
            import subprocess
            try:
                subprocess.Popen([
                    'notify-send',
                    title,
                    message
                ])
                return True
            except (FileNotFoundError, subprocess.SubprocessError):
                logger.warning("notify-send not installed, falling back to system tray")
                return show_notification(title, message)

        else:
            # Unknown platform, fall back to system tray
            logger.warning(f"Unknown platform {system}, falling back to system tray")
            return show_notification(title, message)

    except Exception as e:
        logger.error(f"Error showing platform notification: {e}")
        return show_notification(title, message)  # Fall back to system tray
