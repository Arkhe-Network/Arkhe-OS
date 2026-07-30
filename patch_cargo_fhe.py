import os
import re

base_dir = "/app/safe-core"

with open(os.path.join(base_dir, "Cargo.toml"), "r") as f:
    content = f.read()

# Add dependencies explicitly retaining formatting
new_deps = """
async-trait = "0.1"
tonic = { version = "0.12", features = ["tls", "tls-roots"] }
prost = "0.13"
uuid = { version = "1.12", features = ["v4", "serde"] }
chrono = { version = "0.4", features = ["serde"] }
reqwest = { version = "0.12", features = ["json", "rustls-tls"] }
serde_json = "1.0"
metrics = "0.23"
prometheus = "0.13"
hex = "0.4"
tfhe = { version = "0.11", features = ["integer", "boolean", "serde"] }
bincode = "1.3"
zeroize = { version = "1.8", features = ["derive"] }
getrandom = "0.2"
criterion = "0.5"
rand = "0.8"
"""

if "tfhe =" not in content:
    content = content.replace("[workspace.dependencies]", "[workspace.dependencies]\n" + new_deps)

with open(os.path.join(base_dir, "Cargo.toml"), "w") as f:
    f.write(content)
