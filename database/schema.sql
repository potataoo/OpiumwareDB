CREATE TABLE IF NOT EXISTS `potatoes` (
  `user_id` varchar(20) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS `default_channel` (
  `channel_id` varchar(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS `compromised_accounts` (
  `user_id` varchar(20) NOT NULL UNIQUE,
  `guild_id` varchar(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS `scam_hashes` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `algo` TEXT NOT NULL,
  `hash` TEXT NOT NULL,
  `added_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(algo, hash)
);

CREATE TABLE IF NOT EXISTS `training_images` (
  `filename` TEXT NOT NULL PRIMARY KEY,
  `label` TEXT NOT NULL DEFAULT 'pending',
  `phash` TEXT,
  `dhash` TEXT,
  `ahash` TEXT,
  `chash` TEXT,
  `confidence` REAL,
  `confirmed_by` varchar(20),
  `added_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `model_versions` (
  `version` INTEGER PRIMARY KEY,
  `accuracy` REAL,
  `train_n` INTEGER,
  `n` INTEGER,
  `positives` INTEGER,
  `negatives` INTEGER,
  `created_by` varchar(20),
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);