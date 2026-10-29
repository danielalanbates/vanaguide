# Isolated local database port

`VG_DBPORT` selects the MariaDB TCP port for `tools/client.sh` (default3306). Set it to the private fixture's port, for example47949, when reviving or checking a dedicated local test character. The host remains literal127.0.0.1; user/database remain xiuser/xidb and the password stays in the environment, read from VG_DBPASS. The port must contain digits and fall within1–65535, validated before any action.

Eleven shell fixtures and sixteen inventory guard tests pass. The SQL fixture replaces the absolute MariaDB command with a shell function and verifies loopback host, private port and no password in printed arguments; no database/client/server runs. Configure the server's database port to the same private instance before any live test. This does not create, initialize or launch a server.

Current recovery has only18GB available in Downloads, so do not blindly copy the full FFXI installation. Use a separate mutable prefix and client configuration with a carefully scoped read-only asset strategy, or regain sufficient space first. Keep credentials, database files and character captures private/ignored.
