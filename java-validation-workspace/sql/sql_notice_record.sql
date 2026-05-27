CREATE TABLE `sql_notice_record` (
  `id` bigint NOT NULL COMMENT '主键ID',
  `notice_title` varchar(128) NOT NULL COMMENT '通知标题',
  `notice_amount` decimal(12,2) DEFAULT NULL COMMENT '通知金额',
  `enabled_flag` tinyint DEFAULT NULL COMMENT '启用标识',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`)
) COMMENT='SQL通知记录';
