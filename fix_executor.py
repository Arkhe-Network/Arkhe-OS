import re

with open('safe-core/crates/action-executor/src/sandbox.rs', 'r') as f:
    text = f.read()

# Fix deadlock & thread starvation in wait_child_with_timeout
# Also tokio process issues.
# We will use std::process::Command with pre_exec to apply landlock
# Actually tokio::process::Command does not have pre_exec directly exposed in the same way, but let's see.
# Wait, we can use tokio::process::Command and we don't need to fork manually!
