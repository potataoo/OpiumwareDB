CREATE TABLE IF NOT EXISTS `potatoes` (
  `user_id` varchar(20) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS `default_channel` (
  `channel_id` varchar(20) NOT NULL
);