-- ------------------------
-- Script for generating a new (empty) coffee database
-- -------------------

-- DANGER DANGER DANGER --
--------------------------
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS transactionlog;
DROP TRIGGER IF EXISTS update_transactions;
DROP TRIGGER IF EXISTS insert_transactions;
DROP TRIGGER IF EXISTS delete_transactions;

CREATE TABLE users (
	crsid TEXT PRIMARY KEY,
	rfid INTEGER UNIQUE,
	debt INTEGER,
	salt BLOB,
	vkey BLOB,
	access_level INTEGER DEFAULT 0
	);
	

CREATE TABLE transactions (
	ts DATETIME NOT NULL,
	crsid TEXT NOT NULL, -- trusted
	rfid INTEGER, -- for convenience
	type TEXT NOT NULL,
	debit INTEGER NOT NULL,
	ncoffee INTEGER NOT NULL
	);

-- watchdog
CREATE TABLE transactionlog(
	log_ts DATETIME,
	operation TEXT,
	ts DATETIME,
	ts_new DATETIME,
	rfid DATETIME,
	rfid_new DATETIME,
	crsid TEXT,
	crsid_new TEXT,
	type TEXT,
	type_new TEXT,
	debit INTEGER,
	debit_new INTEGER,
	ncoffee INTEGER,
	ncoffee_new INTEGER);


CREATE TRIGGER update_transactions AFTER UPDATE ON transactions
BEGIN
	INSERT INTO transactionlog
	(log_ts, operation,
		ts, rfid, crsid, type, debit, ncoffee,
		ts_new, rfid_new, crsid_new, type_new, debit_new, ncoffee_new)
	VALUES
	(DATETIME('NOW'), 'UPDATE', old.ts, old.rfid, old.crsid, old.type, old.debit, old.ncoffee,
			new.ts, new.rfid, new.crsid, new.debit, new.type, new.ncoffee);
END;


CREATE TRIGGER insert_transactions AFTER INSERT ON transactions
BEGIN
	INSERT INTO transactionlog
	(log_ts, operation,
		ts_new, rfid_new, crsid_new, type_new, debit_new, ncoffee_new)
	VALUES
	(DATETIME('NOW'), 'INSERT',
			new.ts, new.rfid, new.crsid, new.type, new.debit, new.ncoffee);
END;


CREATE TRIGGER delete_transactions AFTER DELETE ON transactions
BEGIN
	INSERT INTO transactionlog
	(log_ts, operation,
		ts, rfid, crsid, type, debit, ncoffee)
	VALUES
	(DATETIME('NOW'), 'DELETE', old.ts, old.rfid, old.crsid, old.type, old.debit, old.ncoffee);
END;
