# gimp_comfy_bridge/extensions/permissions.py

"""
Extension Permission System

Manages permissions for extension capabilities and security.
"""

from typing import Dict, List, Set, Optional
from enum import Enum
from dataclasses import dataclass

class Permission(Enum):
    """Available extension permissions."""

    # File system access
    FILE_SYSTEM_READ = "file_system_read"
    FILE_SYSTEM_WRITE = "file_system_write"

    # Network access
    NETWORK_HTTP = "network_http"
    NETWORK_WEBSOCKET = "network_websocket"

    # UI capabilities
    UI_INJECTION = "ui_injection"
    UI_DIALOGS = "ui_dialogs"

    # Asset system
    ASSET_ACCESS = "asset_access"
    ASSET_CREATE = "asset_create"
    ASSET_MODIFY = "asset_modify"

    # Workflow system
    WORKFLOW_EXECUTION = "workflow_execution"
    WORKFLOW_CREATE = "workflow_create"
    WORKFLOW_MODIFY = "workflow_modify"

    # Template system
    TEMPLATE_GENERATION = "template_generation"
    TEMPLATE_MODIFY = "template_modify"

    # Brand kit system
    BRAND_KIT_ACCESS = "brand_kit_access"
    BRAND_KIT_MODIFY = "brand_kit_modify"

    # Copywriting system
    COPYWRITING_ACCESS = "copywriting_access"
    COPYWRITING_GENERATE = "copywriting_generate"

    # Layout optimization
    LAYOUT_OPTIMIZATION = "layout_optimization"
    LAYOUT_MODIFY = "layout_modify"

    # Marketplace
    MARKETPLACE_ACCESS = "marketplace_access"
    MARKETPLACE_PUBLISH = "marketplace_publish"

    # System access
    SYSTEM_INFO = "system_info"
    CONFIG_ACCESS = "config_access"

@dataclass
class PermissionContext:
    """Context for permission evaluation."""

    extension_id: str
    requested_permissions: List[str]
    operation: str
    resource: Optional[str] = None
    context_data: Optional[Dict] = None

class PermissionManager:
    """Manages extension permissions and security."""

    def __init__(self):
        self._granted_permissions: Dict[str, Set[str]] = {}
        self._permission_rules: Dict[str, callable] = {}

        # Initialize default permission rules
        self._setup_default_rules()

    def grant_permissions(self, extension_id: str, permissions: List[str]) -> None:
        """Grant permissions to an extension."""
        if extension_id not in self._granted_permissions:
            self._granted_permissions[extension_id] = set()

        self._granted_permissions[extension_id].update(permissions)

    def revoke_permissions(self, extension_id: str, permissions: List[str]) -> None:
        """Revoke permissions from an extension."""
        if extension_id in self._granted_permissions:
            self._granted_permissions[extension_id].difference_update(permissions)

    def has_permission(self, extension_id: str, permission: str) -> bool:
        """Check if extension has a specific permission."""
        granted = self._granted_permissions.get(extension_id, set())
        return permission in granted

    def check_permissions(self, context: PermissionContext) -> bool:
        """Check if operation is allowed based on permissions and context."""
        # Check basic permissions
        for perm in context.requested_permissions:
            if not self.has_permission(context.extension_id, perm):
                return False

        # Check permission rules
        for perm in context.requested_permissions:
            rule = self._permission_rules.get(perm)
            if rule and not rule(context):
                return False

        return True

    def get_granted_permissions(self, extension_id: str) -> List[str]:
        """Get all granted permissions for an extension."""
        return list(self._granted_permissions.get(extension_id, set()))

    def clear_permissions(self, extension_id: str) -> None:
        """Clear all permissions for an extension."""
        self._granted_permissions.pop(extension_id, None)

    def _setup_default_rules(self) -> None:
        """Set up default permission validation rules."""

        # File system rules
        def file_system_rule(context: PermissionContext) -> bool:
            # Restrict certain paths
            restricted_paths = ['/system', '/config', '/extensions']
            if context.resource and any(path in context.resource for path in restricted_paths):
                return False
            return True

        self._permission_rules[Permission.FILE_SYSTEM_READ.value] = file_system_rule
        self._permission_rules[Permission.FILE_SYSTEM_WRITE.value] = file_system_rule

        # Network rules
        def network_rule(context: PermissionContext) -> bool:
            # Allow HTTP/HTTPS, restrict other protocols
            if context.resource:
                if not (context.resource.startswith('http://') or context.resource.startswith('https://')):
                    return False
            return True

        self._permission_rules[Permission.NETWORK_HTTP.value] = network_rule

        # UI injection rules
        def ui_injection_rule(context: PermissionContext) -> bool:
            # Limit UI injection to safe areas
            safe_panels = ['toolbox', 'sidebar', 'toolbar']
            if context.resource and context.resource not in safe_panels:
                return False
            return True

        self._permission_rules[Permission.UI_INJECTION.value] = ui_injection_rule

    def add_permission_rule(self, permission: str, rule: callable) -> None:
        """Add a custom permission validation rule."""
        self._permission_rules[permission] = rule

    def remove_permission_rule(self, permission: str) -> None:
        """Remove a permission validation rule."""
        self._permission_rules.pop(permission, None)

    def validate_permission_request(self, extension_id: str, permissions: List[str]) -> List[str]:
        """Validate a permission request and return any issues."""
        issues = []

        # Check for dangerous permission combinations
        dangerous_combos = [
            {Permission.FILE_SYSTEM_WRITE.value, Permission.NETWORK_HTTP.value},
            {Permission.SYSTEM_INFO.value, Permission.CONFIG_ACCESS.value},
            {Permission.UI_INJECTION.value, Permission.FILE_SYSTEM_WRITE.value}
        ]

        requested_set = set(permissions)
        for combo in dangerous_combos:
            if combo.issubset(requested_set):
                issues.append(f"Dangerous permission combination: {combo}")

        # Check for unknown permissions
        all_permissions = {p.value for p in Permission}
        for perm in permissions:
            if perm not in all_permissions:
                issues.append(f"Unknown permission: {perm}")

        return issues