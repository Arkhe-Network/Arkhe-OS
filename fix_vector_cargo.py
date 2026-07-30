import re

with open('safe-core/crates/memory-system/Cargo.toml', 'r') as f:
    text = f.read()

text += """
rand = "0.8"
"""

with open('safe-core/crates/memory-system/Cargo.toml', 'w') as f:
    f.write(text)
