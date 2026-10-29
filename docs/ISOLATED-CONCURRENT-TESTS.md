# Concurrent hosted play and local fixture testing

The strict default guard is unchanged. An explicitly marked copied fixture may exclude unrelated hosted loaders/carriers only after their executable identity, single explicit remote endpoint and disjoint working directory are verified. Unreadable directories, unknown clients, duplicate/missing endpoints and other local loaders fail closed. The selected client must still satisfy the original exact-loopback/install checks. No hosted command is delivered.

The marker .vanaguide-isolated.json contains the exact resolved game path and allow_concurrent_hosted=true. The guard verifies independent registry files, no symlinks anywhere in mutable addons/config/scripts trees, and a loopback boot profile before applying scope. Shared immutable game assets may remain separate references; no updater runs against them. This mode is for copied local fixtures, never shared installs.

Validation:18 synthetic guard tests and11 shell fixtures pass. Marker/symlink rejection and disjoint hosted/local selection are covered. Runtime concurrency and live quest acceptance remain separate checks.
