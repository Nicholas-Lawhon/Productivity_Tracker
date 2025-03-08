from src.services.db_service import DatabaseService
from src.utils.path_utils import get_project_root
import os


def main():
    # Use path_utils to get project root
    project_root = get_project_root()

    # Define database path relative to project root
    db_path = os.path.join(project_root, 'data', 'local_db.sqlite')
    log_dir = os.path.join(project_root, 'logs')

    print(f"Using database at: {db_path}")
    print(f"Using logs directory: {log_dir}")

    # Create DatabaseService instance with both paths
    db_service = DatabaseService(db_path, log_dir)

    # Test adding a task
    task_id = db_service.add_session_task(
        date="2023-11-06",
        time_elapsed=1.5,
        task_name="Testing Database Implementation"
    )
    print(f"Added task with ID: {task_id}")

    # Test retrieving all tasks
    all_tasks = db_service.get_all_tasks()
    print(f"Total tasks: {len(all_tasks)}")
    print("Tasks:", all_tasks)

    # Test getting unsynced tasks
    unsynced = db_service.get_unsynced_tasks()
    print(f"Unsynced tasks: {len(unsynced)}")

    # Test marking as synced
    success = db_service.mark_as_synced(task_id)
    print(f"Mark as synced: {'Success' if success else 'Failed'}")

    # Verify it's now synced
    unsynced_after = db_service.get_unsynced_tasks()
    print(f"Unsynced tasks after: {len(unsynced_after)}")


if __name__ == "__main__":
    main()
