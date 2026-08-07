-- Skill packages are filesystem-owned. Run the legacy data export before this migration.
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `agents_skills`;
DROP TABLE IF EXISTS `skill_files`;
DROP TABLE IF EXISTS `skills`;

SET FOREIGN_KEY_CHECKS = 1;
