-- The unified sandbox replaces the old workspace/python/bash/skill tools.
-- Keep this migration idempotent so it is safe to run during deployment retry.
START TRANSACTION;

INSERT INTO `agents_builtin_tools` (`agent_id`, `tool_type`)
SELECT DISTINCT old_bindings.`agent_id`, 'sandbox'
FROM `agents_builtin_tools` AS old_bindings
WHERE old_bindings.`tool_type` IN ('skill_manager', 'python_exec', 'bash_exec', 'workspace_manager')
  AND NOT EXISTS (
    SELECT 1
    FROM `agents_builtin_tools` AS current_bindings
    WHERE current_bindings.`agent_id` = old_bindings.`agent_id`
      AND current_bindings.`tool_type` = 'sandbox'
  );

DELETE FROM `agents_builtin_tools`
WHERE `tool_type` IN ('skill_manager', 'python_exec', 'bash_exec', 'workspace_manager');

COMMIT;
