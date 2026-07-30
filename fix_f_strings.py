import re
with open("substrates/t/16_2_zvec/cathedral_arkhe_v16_2_zvec.py", "r") as f:
    content = f.read()

# Find lines with f"
for i, line in enumerate(content.splitlines()):
    if 'f"' in line or "f'" in line:
        print(f"Line {i+1}: {line}")
