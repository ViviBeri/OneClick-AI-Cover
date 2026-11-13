# Local job history

The local API stores job metadata in SQLite at `data/jobs.sqlite3`. The database is created automatically when the Windows app starts; no database server or extra Python package is required.

## Stored data

- Job ID and status
- Progress fraction and current stage message
- Creation and last-update timestamps
- Output file path for completed jobs
- Failure or interruption message

Audio, source recordings, voice checkpoints, retrieval indexes, and generated audio are not stored inside SQLite. They remain in their existing local folders.

## Restart behavior

Completed, failed, and cancelled jobs remain available in the local job list after restarting the application. A job that was queued or running when the previous process ended is marked failed with an interruption message. The application does not automatically resume a partially completed Demucs or RVC operation.

## Location and backup

The database lives at `data/jobs.sqlite3` under the application directory. The `data/` directory is ignored by Git. Back up the database separately if job history is important; backing up the database does not back up the referenced audio files.

## Scope

The Gradio Job History tab displays the latest 100 cover generations with status, progress, timestamps, output filenames, and errors. It does not add multi-user access, automatic cleanup, or durable recovery of intermediate processing files.
