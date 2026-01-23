"""
History management for undo/redo operations.
"""

import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from shared.types import HistoryMetadata

logger = logging.getLogger(__name__)

class HistoryManager:
    """
    Manages history snapshots for undo/redo with comprehensive error handling.
    """
    MAX_SESSION_ID_LENGTH = 100
    MAX_STEP_DIRS = 1000  # Prevent runaway directory creation
    MAX_FILE_SIZE_MB = 50  # Maximum file size for copying

    def __init__(self, temp_dir=None):
        """
        Initialize history manager with validation.

        Args:
            temp_dir (Path, optional): Temporary directory.

        Raises:
            ValueError: If temp_dir is invalid.
        """
        if temp_dir is not None:
            if not isinstance(temp_dir, (str, Path)):
                raise ValueError("temp_dir must be a string or Path")
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = Path(__file__).parent.parent / "temp"

        # Validate temp directory
        if not self.temp_dir.exists():
            raise ValueError(f"Temp directory does not exist: {self.temp_dir}")
        if not self.temp_dir.is_dir():
            raise ValueError(f"Temp path is not a directory: {self.temp_dir}")

        self.session_id = None
        self.current_step = 0
        self.max_step = 0
        self.session_dir = None

    def start_session(self, session_id=None):
        """
        Start a new session with comprehensive validation.

        Args:
            session_id (str, optional): Session ID. If None, generate one.

        Raises:
            ValueError: If session_id is invalid.
            RuntimeError: If session cannot be created.
        """
        try:
            if session_id is not None:
                if not isinstance(session_id, str) or not session_id.strip():
                    raise ValueError("session_id must be a non-empty string")
                if len(session_id) > self.MAX_SESSION_ID_LENGTH:
                    raise ValueError(f"session_id too long (> {self.MAX_SESSION_ID_LENGTH} characters)")
                # Basic sanitization - only allow alphanumeric, hyphens, underscores
                if not all(c.isalnum() or c in '-_' for c in session_id):
                    raise ValueError("session_id contains invalid characters")
                self.session_id = session_id
            else:
                self.session_id = str(uuid4())

            self.session_dir = self.temp_dir / "sessions" / self.session_id

            # Check if session already exists and handle it
            if self.session_dir.exists():
                if not self.session_dir.is_dir():
                    raise RuntimeError(f"Session path exists but is not a directory: {self.session_dir}")
                logger.warning(f"Session {self.session_id} already exists, resuming")
                # Try to resume existing session
                self._load_session_state()
            else:
                self.session_dir.mkdir(parents=True, exist_ok=True)

            self.current_step = 0
            self.max_step = 0
            logger.info(f"Started session {self.session_id}")
        except (OSError, PermissionError) as e:
            raise RuntimeError(f"Cannot create session directory: {e}")
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            raise

    def _load_session_state(self):
        """
        Load existing session state from disk.
        """
        try:
            # Find the highest step number
            step_dirs = [d for d in self.session_dir.iterdir() if d.is_dir() and d.name.startswith("step_")]
            if step_dirs:
                step_numbers = []
                for step_dir in step_dirs:
                    try:
                        step_num = int(step_dir.name.split("_")[1])
                        step_numbers.append(step_num)
                    except (ValueError, IndexError):
                        logger.warning(f"Invalid step directory name: {step_dir.name}")
                        continue

                if step_numbers:
                    self.max_step = max(step_numbers)
                    self.current_step = self.max_step
                    logger.info(f"Resumed session with {self.max_step} steps")
        except Exception as e:
            logger.warning(f"Failed to load session state: {e}")
            # Reset to safe state
            self.current_step = 0
            self.max_step = 0

    def next_step_dir(self):
        """
        Get the next step directory with safety checks.

        Returns:
            Path: Path to the next step directory.

        Raises:
            RuntimeError: If step directory cannot be created.
            ValueError: If step limit exceeded.
        """
        if not self.session_id or not self.session_dir:
            raise RuntimeError("No active session")

        try:
            # Check step limit
            if self.current_step >= self.MAX_STEP_DIRS:
                raise ValueError(f"Maximum step limit ({self.MAX_STEP_DIRS}) exceeded")

            self.current_step += 1
            self.max_step = max(self.max_step, self.current_step)
            step_dir = self.session_dir / f"step_{self.current_step:04d}"

            # Check if step directory already exists (shouldn't happen in normal operation)
            if step_dir.exists():
                logger.warning(f"Step directory already exists: {step_dir}")
                # Remove it to ensure clean state
                if step_dir.is_dir():
                    shutil.rmtree(step_dir)

            step_dir.mkdir(exist_ok=True)
            return step_dir
        except (OSError, PermissionError) as e:
            raise RuntimeError(f"Cannot create step directory: {e}")
        except Exception as e:
            logger.error(f"Failed to create next step dir: {e}")
            raise

    def save_step(self, input_path=None, mask_path=None, output_path=None, params=None, notes=""):
        """
        Save a step snapshot with comprehensive validation and error handling.

        Args:
            input_path (str, optional): Path to input image.
            mask_path (str, optional): Path to mask image.
            output_path (str): Path to output image.
            params (dict): Parameters.
            notes (str): Notes for the step.

        Raises:
            ValueError: If required parameters are invalid.
            RuntimeError: If files cannot be saved.
        """
        if not self.session_id or not self.session_dir:
            raise RuntimeError("No active session")

        if not output_path:
            raise ValueError("output_path is required")

        try:
            step_dir = self.session_dir / f"step_{self.current_step:04d}"

            # Validate and copy input file
            if input_path:
                input_path = Path(input_path)
                if not input_path.exists():
                    logger.warning(f"Input file does not exist: {input_path}")
                elif not input_path.is_file():
                    logger.warning(f"Input path is not a file: {input_path}")
                elif input_path.stat().st_size > self.MAX_FILE_SIZE_MB * 1024 * 1024:
                    logger.warning(f"Input file too large: {input_path}")
                else:
                    shutil.copy(input_path, step_dir / "input.png")

            # Validate and copy mask file
            if mask_path:
                mask_path = Path(mask_path)
                if not mask_path.exists():
                    logger.warning(f"Mask file does not exist: {mask_path}")
                elif not mask_path.is_file():
                    logger.warning(f"Mask path is not a file: {mask_path}")
                elif mask_path.stat().st_size > self.MAX_FILE_SIZE_MB * 1024 * 1024:
                    logger.warning(f"Mask file too large: {mask_path}")
                else:
                    shutil.copy(mask_path, step_dir / "mask.png")

            # Validate and copy output file (required)
            output_path = Path(output_path)
            if not output_path.exists():
                raise ValueError(f"Output file does not exist: {output_path}")
            if not output_path.is_file():
                raise ValueError(f"Output path is not a file: {output_path}")
            if output_path.stat().st_size > self.MAX_FILE_SIZE_MB * 1024 * 1024:
                raise ValueError(f"Output file too large: {output_path}")
            shutil.copy(output_path, step_dir / "output.png")

            # Validate and write params.json
            params = params or {}
            if not isinstance(params, dict):
                raise ValueError("params must be a dict")
            # Sanitize params to ensure JSON serializable
            sanitized_params = self._sanitize_params(params)
            with open(step_dir / "params.json", 'w', encoding='utf-8') as f:
                json.dump(sanitized_params, f, indent=2, ensure_ascii=False)

            # Validate and write meta.json
            meta = {
                "step": self.current_step,
                "timestamp": datetime.now().isoformat(),
                "workflow": params.get("workflow_name", "") if isinstance(params, dict) else "",
                "mode": params.get("mode", "") if isinstance(params, dict) else "",
                "input_file": "input.png" if input_path and Path(input_path).exists() else None,
                "mask_file": "mask.png" if mask_path and Path(mask_path).exists() else None,
                "output_file": "output.png",
                "params_file": "params.json",
                "notes": str(notes)[:500] if notes else ""  # Limit notes length
            }
            with open(step_dir / "meta.json", 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved step {self.current_step}")
        except (OSError, PermissionError) as e:
            raise RuntimeError(f"File system error saving step: {e}")
        except json.JSONEncodeError as e:
            raise RuntimeError(f"JSON encoding error saving step: {e}")
        except Exception as e:
            logger.error(f"Failed to save step: {e}")
            raise

    def _sanitize_params(self, params):
        """
        Sanitize parameters to ensure JSON serializability.

        Args:
            params: Parameters to sanitize.

        Returns:
            dict: Sanitized parameters.
        """
        if not isinstance(params, dict):
            return {}

        sanitized = {}
        for key, value in params.items():
            try:
                # Test JSON serializability
                json.dumps(value)
                sanitized[key] = value
            except (TypeError, ValueError):
                # Convert non-serializable values to strings
                sanitized[key] = str(value)
        return sanitized

    def can_undo(self):
        """
        Check if undo is possible with validation.

        Returns:
            bool: True if can undo.
        """
        if not self.session_id or not self.session_dir:
            return False
        return self.current_step > 1

    def can_redo(self):
        """
        Check if redo is possible with validation.

        Returns:
            bool: True if can redo.
        """
        if not self.session_id or not self.session_dir:
            return False
        return self.current_step < self.max_step

    def undo(self):
        """
        Perform undo with comprehensive error handling.

        Returns:
            str or None: Path to the output image for the previous step, or None.
        """
        if not self.can_undo():
            logger.warning("Cannot undo: no previous step available")
            return None

        try:
            self.current_step -= 1
            step_dir = self.session_dir / f"step_{self.current_step:04d}"

            if not step_dir.exists():
                logger.error(f"Step directory does not exist: {step_dir}")
                return None

            output_path = step_dir / "output.png"
            if not output_path.exists():
                logger.error(f"Output file does not exist: {output_path}")
                return None

            # Validate file is readable
            if not output_path.is_file():
                logger.error(f"Output path is not a file: {output_path}")
                return None

            logger.info(f"Undid to step {self.current_step}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to undo: {e}")
            return None

    def redo(self):
        """
        Perform redo with comprehensive error handling.

        Returns:
            str or None: Path to the output image for the next step, or None.
        """
        if not self.can_redo():
            logger.warning("Cannot redo: no next step available")
            return None

        try:
            self.current_step += 1
            step_dir = self.session_dir / f"step_{self.current_step:04d}"

            if not step_dir.exists():
                logger.error(f"Step directory does not exist: {step_dir}")
                return None

            output_path = step_dir / "output.png"
            if not output_path.exists():
                logger.error(f"Output file does not exist: {output_path}")
                return None

            # Validate file is readable
            if not output_path.is_file():
                logger.error(f"Output path is not a file: {output_path}")
                return None

            logger.info(f"Redid to step {self.current_step}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to redo: {e}")
            return None

    def truncate_forward_history(self):
        """
        Truncate forward history after undo with safe deletion.
        """
        if not self.session_id or not self.session_dir:
            return

        try:
            deleted_count = 0
            for step in range(self.current_step + 1, self.max_step + 1):
                step_dir = self.session_dir / f"step_{step:04d}"
                if step_dir.exists():
                    if not step_dir.is_dir():
                        logger.warning(f"Step path is not a directory: {step_dir}")
                        continue

                    try:
                        shutil.rmtree(step_dir)
                        deleted_count += 1
                        logger.debug(f"Truncated step {step}")
                    except (OSError, PermissionError) as e:
                        logger.error(f"Failed to delete step directory {step}: {e}")
                        continue

            self.max_step = self.current_step
            if deleted_count > 0:
                logger.info(f"Truncated {deleted_count} forward history steps")
        except Exception as e:
            logger.error(f"Failed to truncate forward history: {e}")
            # Don't raise - this is not a critical failure

    def load_meta(self, step: int):
        """
        Load metadata for a step with comprehensive error handling.

        Args:
            step (int): Step number.

        Returns:
            HistoryMetadata or None: Metadata for the step, or None if not found or invalid.
        """
        if not self.session_id or not self.session_dir:
            return None

        if not isinstance(step, int) or step < 1 or step > self.max_step:
            logger.warning(f"Invalid step number: {step}")
            return None

        try:
            step_dir = self.session_dir / f"step_{step:04d}"
            if not step_dir.exists():
                logger.warning(f"Step directory does not exist: {step_dir}")
                return None

            meta_path = step_dir / "meta.json"
            if not meta_path.exists():
                logger.warning(f"Meta file does not exist: {meta_path}")
                return None

            if not meta_path.is_file():
                logger.warning(f"Meta path is not a file: {meta_path}")
                return None

            # Check file size (prevent memory exhaustion)
            file_size = meta_path.stat().st_size
            if file_size > 1024 * 1024:  # 1MB limit
                logger.warning(f"Meta file too large: {file_size} bytes")
                return None

            with open(meta_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate required fields
            required_fields = ["step", "timestamp", "workflow", "mode", "output_file"]
            for field in required_fields:
                if field not in data:
                    logger.warning(f"Meta file missing required field: {field}")
                    return None

            # Validate data types
            if not isinstance(data.get("step"), int):
                logger.warning("Meta step field is not an integer")
                return None

            return HistoryMetadata(**data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in meta file for step {step}: {e}")
            return None
        except (OSError, PermissionError) as e:
            logger.error(f"File system error loading meta for step {step}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading meta for step {step}: {e}")
            return None