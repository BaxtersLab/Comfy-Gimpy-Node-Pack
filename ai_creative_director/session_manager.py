"""
Collaborative Session Manager
Manages multi-user creative sessions and real-time collaboration
"""

import json
import os
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import uuid

class CollaborativeSessionManager:
    """
    Manages collaborative creative sessions with real-time features
    """

    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Session storage
        self.active_sessions = {}
        self.session_history = {}
        self.participant_sessions = {}  # user_id -> set of session_ids

        # Collaboration features
        self.session_lock = threading.Lock()
        self.cleanup_thread = None
        self.running = False

        # Session data persistence
        self.session_data_path = os.path.join(os.path.dirname(__file__), '..', 'session_data')
        os.makedirs(self.session_data_path, exist_ok=True)

        self._start_cleanup_thread()

    def create_session(self, session_name: str, creator_id: str,
                      participants: Optional[List[str]] = None,
                      session_type: str = "creative") -> str:
        """
        Create a new collaborative session

        Args:
            session_name: Name of the session
            creator_id: ID of the session creator
            participants: List of participant user IDs
            session_type: Type of session (creative, review, etc.)

        Returns:
            Session ID
        """
        try:
            session_id = str(uuid.uuid4())

            with self.session_lock:
                session = {
                    "id": session_id,
                    "name": session_name,
                    "creator": creator_id,
                    "type": session_type,
                    "participants": participants or [creator_id],
                    "created_at": datetime.now(),
                    "last_activity": datetime.now(),
                    "status": "active",
                    "settings": {
                        "max_participants": self.config.get("max_participants", 10),
                        "auto_save": True,
                        "real_time_sync": True,
                        "voting_enabled": True
                    },
                    "data": {
                        "workflow": None,
                        "assets": [],
                        "comments": [],
                        "decisions": [],
                        "votes": {}
                    },
                    "activity_log": [],
                    "permissions": self._initialize_permissions(creator_id, participants or [])
                }

                self.active_sessions[session_id] = session

                # Track participant sessions
                for participant in session["participants"]:
                    if participant not in self.participant_sessions:
                        self.participant_sessions[participant] = set()
                    self.participant_sessions[participant].add(session_id)

                # Log session creation
                self._log_session_activity(session_id, "created", creator_id,
                                         f"Session '{session_name}' created by {creator_id}")

                self.logger.info(f"Created collaborative session {session_id}: {session_name}")
                return session_id

        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            return None

    def _initialize_permissions(self, creator_id: str, participants: List[str]) -> Dict[str, Any]:
        """Initialize session permissions"""
        permissions = {
            "owner": creator_id,
            "admins": [creator_id],
            "editors": participants.copy(),
            "viewers": [],
            "permissions": {
                "edit_workflow": "editors",
                "add_comments": "all",
                "vote_decisions": "all",
                "invite_participants": "admins",
                "change_settings": "owner"
            }
        }

        return permissions

    def join_session(self, session_id: str, user_id: str) -> bool:
        """
        Join an existing collaborative session

        Args:
            session_id: Session to join
            user_id: User ID joining the session

        Returns:
            Success status
        """
        try:
            with self.session_lock:
                if session_id not in self.active_sessions:
                    return False

                session = self.active_sessions[session_id]

                # Check if session is full
                if len(session["participants"]) >= session["settings"]["max_participants"]:
                    return False

                # Add participant if not already in session
                if user_id not in session["participants"]:
                    session["participants"].append(user_id)

                    # Track participant sessions
                    if user_id not in self.participant_sessions:
                        self.participant_sessions[user_id] = set()
                    self.participant_sessions[user_id].add(session_id)

                    # Update permissions
                    session["permissions"]["editors"].append(user_id)

                    # Log activity
                    self._log_session_activity(session_id, "joined", user_id,
                                             f"User {user_id} joined the session")

                session["last_activity"] = datetime.now()
                return True

        except Exception as e:
            self.logger.error(f"Failed to join session {session_id}: {e}")
            return False

    def leave_session(self, session_id: str, user_id: str) -> bool:
        """
        Leave a collaborative session

        Args:
            session_id: Session to leave
            user_id: User ID leaving the session

        Returns:
            Success status
        """
        try:
            with self.session_lock:
                if session_id not in self.active_sessions:
                    return False

                session = self.active_sessions[session_id]

                if user_id not in session["participants"]:
                    return False

                # Remove participant
                session["participants"].remove(user_id)

                # Update permissions
                if user_id in session["permissions"]["editors"]:
                    session["permissions"]["editors"].remove(user_id)

                # Remove from participant tracking
                if user_id in self.participant_sessions:
                    self.participant_sessions[user_id].discard(session_id)
                    if not self.participant_sessions[user_id]:
                        del self.participant_sessions[user_id]

                # Log activity
                self._log_session_activity(session_id, "left", user_id,
                                         f"User {user_id} left the session")

                # Check if session should be closed
                if len(session["participants"]) == 0:
                    self._close_session(session_id)
                else:
                    session["last_activity"] = datetime.now()

                return True

        except Exception as e:
            self.logger.error(f"Failed to leave session {session_id}: {e}")
            return False

    def update_session_workflow(self, session_id: str, user_id: str,
                               workflow_data: Dict[str, Any]) -> bool:
        """
        Update the workflow in a collaborative session

        Args:
            session_id: Session ID
            user_id: User making the update
            workflow_data: New workflow data

        Returns:
            Success status
        """
        try:
            with self.session_lock:
                if not self._check_permission(session_id, user_id, "edit_workflow"):
                    return False

                session = self.active_sessions[session_id]
                session["data"]["workflow"] = workflow_data
                session["last_activity"] = datetime.now()

                # Log activity
                self._log_session_activity(session_id, "workflow_updated", user_id,
                                         "Workflow updated in session")

                # Notify other participants
                self._notify_participants(session_id, "workflow_update",
                                        {"user_id": user_id, "timestamp": datetime.now().isoformat()})

                return True

        except Exception as e:
            self.logger.error(f"Failed to update session workflow: {e}")
            return False

    def add_session_comment(self, session_id: str, user_id: str,
                           comment: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a comment to a collaborative session

        Args:
            session_id: Session ID
            user_id: User making the comment
            comment: Comment text
            context: Optional context (node_id, position, etc.)

        Returns:
            Success status
        """
        try:
            with self.session_lock:
                if not self._check_permission(session_id, user_id, "add_comments"):
                    return False

                session = self.active_sessions[session_id]

                comment_data = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "comment": comment,
                    "context": context or {},
                    "timestamp": datetime.now(),
                    "replies": [],
                    "votes": {"up": 0, "down": 0}
                }

                session["data"]["comments"].append(comment_data)
                session["last_activity"] = datetime.now()

                # Log activity
                self._log_session_activity(session_id, "comment_added", user_id,
                                         f"Comment added: {comment[:50]}...")

                return True

        except Exception as e:
            self.logger.error(f"Failed to add session comment: {e}")
            return False

    def vote_on_decision(self, session_id: str, user_id: str,
                        decision_id: str, vote: str) -> bool:
        """
        Vote on a decision in a collaborative session

        Args:
            session_id: Session ID
            user_id: User voting
            decision_id: Decision being voted on
            vote: Vote type (yes, no, abstain)

        Returns:
            Success status
        """
        try:
            with self.session_lock:
                if not self._check_permission(session_id, user_id, "vote_decisions"):
                    return False

                session = self.active_sessions[session_id]

                if "votes" not in session["data"]:
                    session["data"]["votes"] = {}

                if decision_id not in session["data"]["votes"]:
                    session["data"]["votes"][decision_id] = {}

                session["data"]["votes"][decision_id][user_id] = {
                    "vote": vote,
                    "timestamp": datetime.now()
                }

                session["last_activity"] = datetime.now()

                # Log activity
                self._log_session_activity(session_id, "vote_cast", user_id,
                                         f"Vote cast on decision {decision_id}: {vote}")

                return True

        except Exception as e:
            self.logger.error(f"Failed to cast vote: {e}")
            return False

    def get_session_data(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data for a user

        Args:
            session_id: Session ID
            user_id: User requesting data

        Returns:
            Session data if user has access
        """
        try:
            with self.session_lock:
                if session_id not in self.active_sessions:
                    return None

                session = self.active_sessions[session_id]

                if user_id not in session["participants"]:
                    return None

                # Return session data with user-specific permissions
                session_data = session.copy()
                session_data["user_permissions"] = self._get_user_permissions(session, user_id)

                return session_data

        except Exception as e:
            self.logger.error(f"Failed to get session data: {e}")
            return None

    def _check_permission(self, session_id: str, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission in the session"""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]

        if user_id not in session["participants"]:
            return False

        perm_settings = session["permissions"]["permissions"].get(permission, "none")

        if perm_settings == "all":
            return True
        elif perm_settings == "owner" and user_id == session["permissions"]["owner"]:
            return True
        elif perm_settings == "admins" and user_id in session["permissions"]["admins"]:
            return True
        elif perm_settings == "editors" and user_id in session["permissions"]["editors"]:
            return True

        return False

    def _get_user_permissions(self, session: Dict[str, Any], user_id: str) -> Dict[str, bool]:
        """Get all permissions for a user in the session"""
        permissions = {}
        all_perms = ["edit_workflow", "add_comments", "vote_decisions",
                    "invite_participants", "change_settings"]

        for perm in all_perms:
            permissions[perm] = self._check_permission(session["id"], user_id, perm)

        return permissions

    def _log_session_activity(self, session_id: str, activity_type: str,
                            user_id: str, description: str) -> None:
        """Log activity in a session"""
        if session_id not in self.active_sessions:
            return

        session = self.active_sessions[session_id]

        activity = {
            "type": activity_type,
            "user_id": user_id,
            "description": description,
            "timestamp": datetime.now()
        }

        session["activity_log"].append(activity)

        # Keep only recent activities
        if len(session["activity_log"]) > 100:
            session["activity_log"] = session["activity_log"][-100:]

    def _notify_participants(self, session_id: str, notification_type: str,
                           data: Dict[str, Any]) -> None:
        """Notify session participants of changes"""
        # In a real implementation, this would send real-time notifications
        # For now, just log the notification
        session = self.active_sessions.get(session_id)
        if session:
            self.logger.info(f"Notification sent to {len(session['participants'])} participants: {notification_type}")

    def list_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all sessions a user is participating in

        Args:
            user_id: User ID

        Returns:
            List of session summaries
        """
        try:
            with self.session_lock:
                user_sessions = self.participant_sessions.get(user_id, set())
                sessions = []

                for session_id in user_sessions:
                    if session_id in self.active_sessions:
                        session = self.active_sessions[session_id]
                        sessions.append({
                            "id": session_id,
                            "name": session["name"],
                            "type": session["type"],
                            "participants": len(session["participants"]),
                            "last_activity": session["last_activity"],
                            "status": session["status"]
                        })

                return sessions

        except Exception as e:
            self.logger.error(f"Failed to list user sessions: {e}")
            return []

    def get_session_participants(self, session_id: str) -> List[str]:
        """Get list of participants in a session"""
        with self.session_lock:
            session = self.active_sessions.get(session_id)
            return session["participants"] if session else []

    def invite_participant(self, session_id: str, inviter_id: str,
                          invitee_id: str) -> bool:
        """
        Invite a new participant to a session

        Args:
            session_id: Session ID
            inviter_id: User sending the invitation
            invitee_id: User being invited

        Returns:
            Success status
        """
        try:
            with self.session_lock:
                if not self._check_permission(session_id, inviter_id, "invite_participants"):
                    return False

                session = self.active_sessions[session_id]

                # Check if already a participant
                if invitee_id in session["participants"]:
                    return False

                # Check session capacity
                if len(session["participants"]) >= session["settings"]["max_participants"]:
                    return False

                # Add as viewer initially (can be promoted later)
                session["permissions"]["viewers"].append(invitee_id)

                # Log invitation
                self._log_session_activity(session_id, "invitation_sent", inviter_id,
                                         f"Invited user {invitee_id} to session")

                return True

        except Exception as e:
            self.logger.error(f"Failed to invite participant: {e}")
            return False

    def _close_session(self, session_id: str) -> None:
        """Close a collaborative session"""
        try:
            with self.session_lock:
                if session_id not in self.active_sessions:
                    return

                session = self.active_sessions[session_id]

                # Save session to history
                self.session_history[session_id] = {
                    "session": session,
                    "closed_at": datetime.now(),
                    "duration": datetime.now() - session["created_at"]
                }

                # Clean up participant tracking
                for participant in session["participants"]:
                    if participant in self.participant_sessions:
                        self.participant_sessions[participant].discard(session_id)
                        if not self.participant_sessions[participant]:
                            del self.participant_sessions[participant]

                # Remove from active sessions
                del self.active_sessions[session_id]

                # Save to disk
                self._save_session_data(session_id, self.session_history[session_id])

                self.logger.info(f"Closed session {session_id}")

        except Exception as e:
            self.logger.error(f"Failed to close session {session_id}: {e}")

    def _save_session_data(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Save session data to disk"""
        try:
            filename = f"session_{session_id}.json"
            filepath = os.path.join(self.session_data_path, filename)

            with open(filepath, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save session data: {e}")

    def _start_cleanup_thread(self) -> None:
        """Start background cleanup thread"""
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired sessions"""
        while self.running:
            try:
                self._cleanup_expired_sessions()
                time.sleep(300)  # Check every 5 minutes
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
                time.sleep(60)

    def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions"""
        try:
            with self.session_lock:
                current_time = datetime.now()
                timeout = timedelta(seconds=self.config.get("session_timeout", 3600))

                expired_sessions = []
                for session_id, session in self.active_sessions.items():
                    if current_time - session["last_activity"] > timeout:
                        expired_sessions.append(session_id)

                for session_id in expired_sessions:
                    self.logger.info(f"Auto-closing expired session {session_id}")
                    self._close_session(session_id)

        except Exception as e:
            self.logger.error(f"Session cleanup error: {e}")

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about collaborative sessions"""
        with self.session_lock:
            return {
                "active_sessions": len(self.active_sessions),
                "total_participants": len(self.participant_sessions),
                "historical_sessions": len(self.session_history),
                "session_types": self._count_session_types()
            }

    def _count_session_types(self) -> Dict[str, int]:
        """Count sessions by type"""
        type_counts = {}
        for session in self.active_sessions.values():
            session_type = session.get("type", "unknown")
            type_counts[session_type] = type_counts.get(session_type, 0) + 1

        return type_counts

    def export_session_data(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Export session data for a user

        Args:
            session_id: Session ID
            user_id: User requesting export

        Returns:
            Session data for export
        """
        try:
            with self.session_lock:
                if not self._check_permission(session_id, user_id, "change_settings"):
                    return None

                session = self.active_sessions.get(session_id)
                if not session:
                    return None

                # Create export data
                export_data = {
                    "session_info": {
                        "id": session["id"],
                        "name": session["name"],
                        "type": session["type"],
                        "created_at": session["created_at"],
                        "participants": session["participants"]
                    },
                    "data": session["data"],
                    "activity_log": session["activity_log"],
                    "exported_at": datetime.now(),
                    "exported_by": user_id
                }

                return export_data

        except Exception as e:
            self.logger.error(f"Failed to export session data: {e}")
            return None

    def shutdown(self) -> None:
        """Shutdown the session manager"""
        self.running = False

        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)

        # Close all active sessions
        with self.session_lock:
            active_ids = list(self.active_sessions.keys())
            for session_id in active_ids:
                self._close_session(session_id)

        self.logger.info("Collaborative Session Manager shut down")