BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "auth_group" (
	"id"	integer NOT NULL,
	"name"	varchar(150) NOT NULL UNIQUE,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "auth_group_permissions" (
	"id"	integer NOT NULL,
	"group_id"	integer NOT NULL,
	"permission_id"	integer NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("group_id") REFERENCES "auth_group"("id") DEFERRABLE INITIALLY DEFERRED,
	FOREIGN KEY("permission_id") REFERENCES "auth_permission"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "auth_permission" (
	"id"	integer NOT NULL,
	"content_type_id"	integer NOT NULL,
	"codename"	varchar(100) NOT NULL,
	"name"	varchar(255) NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("content_type_id") REFERENCES "django_content_type"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "auth_user" (
	"id"	integer NOT NULL,
	"password"	varchar(128) NOT NULL,
	"last_login"	datetime,
	"is_superuser"	bool NOT NULL,
	"username"	varchar(150) NOT NULL UNIQUE,
	"last_name"	varchar(150) NOT NULL,
	"email"	varchar(254) NOT NULL,
	"is_staff"	bool NOT NULL,
	"is_active"	bool NOT NULL,
	"date_joined"	datetime NOT NULL,
	"first_name"	varchar(150) NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "auth_user_groups" (
	"id"	integer NOT NULL,
	"user_id"	integer NOT NULL,
	"group_id"	integer NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("group_id") REFERENCES "auth_group"("id") DEFERRABLE INITIALLY DEFERRED,
	FOREIGN KEY("user_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "auth_user_user_permissions" (
	"id"	integer NOT NULL,
	"user_id"	integer NOT NULL,
	"permission_id"	integer NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("permission_id") REFERENCES "auth_permission"("id") DEFERRABLE INITIALLY DEFERRED,
	FOREIGN KEY("user_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "portfolio_holding" (
	"id"	integer NOT NULL,
	"symbol"	varchar(20) NOT NULL,
	"name"	varchar(100) NOT NULL,
	"asset_type"	varchar(10) NOT NULL,
	"quantity"	decimal NOT NULL,
	"avg_price"	decimal NOT NULL,
	"current_price"	decimal NOT NULL,
	"last_updated"	datetime NOT NULL,
	"portfolio_id"	bigint NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("portfolio_id") REFERENCES "portfolio_portfolio"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "portfolio_portfolio" (
	"id"	integer NOT NULL,
	"name"	varchar(100) NOT NULL,
	"created_at"	datetime NOT NULL,
	"updated_at"	datetime NOT NULL,
	"user_id"	integer NOT NULL UNIQUE,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("user_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "portfolio_portfoliosnapshot" (
	"id"	integer NOT NULL,
	"date"	date NOT NULL,
	"total_value"	decimal NOT NULL,
	"total_invested"	decimal NOT NULL,
	"profit_loss"	decimal NOT NULL,
	"portfolio_id"	bigint NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("portfolio_id") REFERENCES "portfolio_portfolio"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "portfolio_pricealert" (
	"id"	integer NOT NULL,
	"symbol"	varchar(20) NOT NULL,
	"name"	varchar(100) NOT NULL,
	"alert_type"	varchar(10) NOT NULL,
	"target_price"	decimal NOT NULL,
	"current_price"	decimal NOT NULL,
	"is_triggered"	bool NOT NULL,
	"is_active"	bool NOT NULL,
	"created_at"	datetime NOT NULL,
	"triggered_at"	datetime,
	"user_id"	integer NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("user_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "portfolio_transaction" (
	"id"	integer NOT NULL,
	"symbol"	varchar(20) NOT NULL,
	"name"	varchar(100) NOT NULL,
	"asset_type"	varchar(10) NOT NULL,
	"transaction_type"	varchar(10) NOT NULL,
	"quantity"	decimal NOT NULL,
	"price"	decimal NOT NULL,
	"total_amount"	decimal NOT NULL,
	"date"	datetime NOT NULL,
	"notes"	text,
	"portfolio_id"	bigint NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("portfolio_id") REFERENCES "portfolio_portfolio"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "portfolio_watchlistitem" (
	"id"	integer NOT NULL,
	"symbol"	varchar(20) NOT NULL,
	"name"	varchar(100) NOT NULL,
	"asset_type"	varchar(10) NOT NULL,
	"current_price"	decimal NOT NULL,
	"added_at"	datetime NOT NULL,
	"user_id"	integer NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("user_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS "stocks_stockcache" (
	"id"	integer NOT NULL,
	"symbol"	varchar(20) NOT NULL UNIQUE,
	"name"	varchar(100) NOT NULL,
	"asset_type"	varchar(10) NOT NULL,
	"current_price"	decimal NOT NULL,
	"open_price"	decimal NOT NULL,
	"high_price"	decimal NOT NULL,
	"low_price"	decimal NOT NULL,
	"volume"	bigint NOT NULL,
	"market_cap"	bigint NOT NULL,
	"week_52_high"	decimal NOT NULL,
	"week_52_low"	decimal NOT NULL,
	"sector"	varchar(100),
	"last_updated"	datetime NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "users_profile" (
	"id"	integer NOT NULL,
	"bio"	text,
	"avatar"	varchar(100),
	"created_at"	datetime NOT NULL,
	"updated_at"	datetime NOT NULL,
	"user_id"	integer NOT NULL UNIQUE,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("user_id") REFERENCES "auth_user"("id") DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX IF NOT EXISTS "auth_group_permissions_group_id_b120cbf9" ON "auth_group_permissions" (
	"group_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "auth_group_permissions_group_id_permission_id_0cd325b0_uniq" ON "auth_group_permissions" (
	"group_id",
	"permission_id"
);
CREATE INDEX IF NOT EXISTS "auth_group_permissions_permission_id_84c5c92e" ON "auth_group_permissions" (
	"permission_id"
);
CREATE INDEX IF NOT EXISTS "auth_permission_content_type_id_2f476e4b" ON "auth_permission" (
	"content_type_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "auth_permission_content_type_id_codename_01ab375a_uniq" ON "auth_permission" (
	"content_type_id",
	"codename"
);
CREATE INDEX IF NOT EXISTS "auth_user_groups_group_id_97559544" ON "auth_user_groups" (
	"group_id"
);
CREATE INDEX IF NOT EXISTS "auth_user_groups_user_id_6a12ed8b" ON "auth_user_groups" (
	"user_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "auth_user_groups_user_id_group_id_94350c0c_uniq" ON "auth_user_groups" (
	"user_id",
	"group_id"
);
CREATE INDEX IF NOT EXISTS "auth_user_user_permissions_permission_id_1fbb5f2c" ON "auth_user_user_permissions" (
	"permission_id"
);
CREATE INDEX IF NOT EXISTS "auth_user_user_permissions_user_id_a95ead1b" ON "auth_user_user_permissions" (
	"user_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "auth_user_user_permissions_user_id_permission_id_14a6b632_uniq" ON "auth_user_user_permissions" (
	"user_id",
	"permission_id"
);
CREATE INDEX IF NOT EXISTS "portfolio_holding_portfolio_id_db168133" ON "portfolio_holding" (
	"portfolio_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "portfolio_holding_portfolio_id_symbol_4d68f0f5_uniq" ON "portfolio_holding" (
	"portfolio_id",
	"symbol"
);
CREATE UNIQUE INDEX IF NOT EXISTS "portfolio_portfoliosnapshot_portfolio_id_date_9df65828_uniq" ON "portfolio_portfoliosnapshot" (
	"portfolio_id",
	"date"
);
CREATE INDEX IF NOT EXISTS "portfolio_portfoliosnapshot_portfolio_id_e24588cd" ON "portfolio_portfoliosnapshot" (
	"portfolio_id"
);
CREATE INDEX IF NOT EXISTS "portfolio_pricealert_user_id_cb0aad5a" ON "portfolio_pricealert" (
	"user_id"
);
CREATE INDEX IF NOT EXISTS "portfolio_transaction_portfolio_id_9a795480" ON "portfolio_transaction" (
	"portfolio_id"
);
CREATE INDEX IF NOT EXISTS "portfolio_watchlistitem_user_id_15b5c190" ON "portfolio_watchlistitem" (
	"user_id"
);
CREATE UNIQUE INDEX IF NOT EXISTS "portfolio_watchlistitem_user_id_symbol_8ddcb849_uniq" ON "portfolio_watchlistitem" (
	"user_id",
	"symbol"
);
COMMIT;
