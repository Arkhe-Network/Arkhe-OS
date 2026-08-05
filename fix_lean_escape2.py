with open("bug_bounty_web3.lean", "r") as f:
    content = f.read()

old_str = """  let d := (r.description.replace "\\\\" "\\\\\\\\").replace "\\"" "\\\\\\""
  let ns := (r.nullSpaceArg.replace "\\\\" "\\\\\\\\").replace "\\"" "\\\\\\"" """
new_str = """  let lean_escape (text : String) : String := (text.replace "\\\\" "\\\\\\\\").replace "\\"" "\\\\\\""
  let d := lean_escape r.description
  let ns := lean_escape r.nullSpaceArg"""

content = content.replace(old_str, new_str)
with open("bug_bounty_web3.lean", "w") as f:
    f.write(content)
