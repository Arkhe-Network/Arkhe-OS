import re

with open('safe-core/crates/memory-system/src/vector.rs', 'r') as f:
    text = f.read()

# Fix the rand module to use actual rand instead of dummy
# We just need to add rand to Cargo.toml and use it
text = text.replace('mod rand {', '#[cfg(not(any()))]\nmod rand {')

with open('safe-core/crates/memory-system/src/vector.rs', 'w') as f:
    f.write(text)
