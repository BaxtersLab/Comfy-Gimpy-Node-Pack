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
    Manages history snapshots for undo/redo.
    """
    def __init__(self, temp_dir=None):
        """
        Initialize history manager.

        Args:
            temp_dir (Path, optional): Temporary directory.
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path(__file__).parent.parent / "temp"
        self.session_id = None
        self.current_step = 0
        self.max_step = 0

    def start_session(self, session_id=None):
        """
        Start a new session.

        Args:
            session_id (str, optional): Session ID. If None, generate one.
        """
        try:
            self.session_id = session_id or str(uuid4())
            self.session_dir = self.temp_dir / "sessions" / self.session_id
            self.session_dir.mkdir(parents=True, exist_ok=True)
            self.current_step = 0
            self.max_step = 0
            logger.info(f"Started session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            raise

    def next_step_dir(self):
        """
        Get the next step directory.

        Returns:
            Path: Path to the next step directory.
        """
        try:
            self.current_step += 1
            self.max_step = self.current_step
            step_dir = self.session_dir / f"step_{self.current_step:04d}"
            step_dir.mkdir(exist_ok=True)
            return step_dir
        except Exception as e:
            logger.error(f"Failed to create next step dir: {e}")
            raise

    def save_step(self, input_path=None, mask_path=None, output_path=None, params=None, notes=""):
        """
        Save a step snapshot.

        Args:
            input_path (str, optional): Path to input image.
            mask_path (str, optional): Path to mask image.
            output_path (str): Path to output image.
            params (dict): Parameters.
            notes (str): Notes for the step.
        """
        try:
            step_dir = self.session_dir / f"step_{self.current_step:04d}"
            
            # Copy files
            if input_path and Path(input_path).exists():
                shutil.copy(input_path, step_dir / "input.png")
            if mask_path and Path(mask_path).exists():
                shutil.copy(mask_path, step_dir / "mask.png")
            if output_path and Path(output_path).exists():
                shutil.copy(output_path, step_dir / "output.png")
            
            # Write params.json
            with open(step_dir / "params.json", 'w') as f:
                json.dump(params or {}, f)
            
            # Write meta.json
            meta = {
                "step": self.current_step,
                "timestamp": datetime.now().isoformat(),
                "workflow": params.get("workflow_name", "") if params else "",
                "mode": params.get("mode", "") if params else "",
                "input_file": "input.png" if input_path else None,
                "mask_file": "mask.png" if mask_path else None,
                "output_file": "output.png",
                "params_file": "params.json",
                "notes": notes
            }
            with open(step_dir / "meta.json", 'w') as f:
                json.dump(meta, f)
            
            logger.info(f"Saved step {self.current_step}")
        except Exception as e:
            logger.error(f"Failed to save step: {e}")
            raise

    def can_undo(self):
        """
        Check if undo is possible.

        Returns:
            bool: True if can undo.
        """
        return self.current_step > 1

    def can_redo(self):
        """
        Check if redo is possible.

        Returns:
            bool: True if can redo.
        """
        return self.current_step < self.max_step

    def undo(self):
        """
        Perform undo.

        Returns:
            str or None: Path to the output image for the previous step, or None.
        """
        try:
            if self.can_undo():
                self.current_step -= 1
                step_dir = self.session_dir / f"step_{self.current_step:04d}"
                output_path = step_dir / "output.png"
                if output_path.exists():
                    logger.info(f"Undid to step {self.current_step}")
                    return str(output_path)
            return None
        except Exception as e:
            logger.error(f"Failed to undo: {e}")
            return None

    def redo(self):
        """
        Perform redo.

        Returns:
            str or None: Path to the output image for the next step, or None.
        """
        try:
            if self.can_redo():
                self.current_step += 1
                step_dir = self.session_dir / f"step_{self.current_step:04d}"
                output_path = step_dir / "output.png"
                if output_path.exists():
                    logger.info(f"Redid to step {self.current_step}")
                    return str(output_path)
            return None
        except Exception as e:
            logger.error(f"Failed to redo: {e}")
            return None

    def truncate_forward_history(self):
        """
        Truncate forward history after undo.
        """
        try:
            for step in range(self.current_step + 1, self.max_step + 1):
                step_dir = self.session_dir / f"step_{step:04d}"
                if step_dir.exists():
                    shutil.rmtree(step_dir)
                    logger.info(f"Truncated step {step}")
            self.max_step = self.current_step
        except Exception as e:
            logger.error(f"Failed to truncate forward history: {e}")
            raise

    def load_meta(self, step: int):
        """
        Load metadata for a step.

        Args:
            step (int): Step number.

        Returns:
            HistoryMetadata: Metadata for the step.
        """
        try:
            step_dir = self.session_dir / f"step_{step:04d}"
            meta_path = step_dir / "meta.json"
            if meta_path.exists():
                with open(meta_path, 'r') as f:
                    data = json.load(f)
                return HistoryMetadata(**data)
            return None
        except Exception as e:
            logger.error(f"Failed to load meta for step {step}: {e}")
            return None