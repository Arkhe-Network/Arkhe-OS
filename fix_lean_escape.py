with open("bug_bounty_web3.lean", "r") as f:
    content = f.read()

old_str = """  let ns := (r.nullSpaceArg.replace "\\\\" "\\\\\\\\").replace "\\"" "\\\\\\""
  s!"⟨{v}, {r.location}, \\"{d}\\", {r.severity}, #[], \\"{ns}\\"⟩" """

new_str = """  let d := (r.description.replace "\\\\" "\\\\\\\\").replace "\\"" "\\\\\\""
  let ns := (r.nullSpaceArg.replace "\\\\" "\\\\\\\\").replace "\\"" "\\\\\\""
  s!"⟨{v}, {r.location}, \\"{d}\\", {r.severity}, #[], \\"{ns}\\"⟩" """

content = content.replace('let ns := (r.nullSpaceArg.replace "\\\\" "\\\\\\\\").replace "\\"" "\\\\\\""\n  s!"⟨{v}, {r.location}, \\"{d}\\", {r.severity}, #[], \\"{ns}\\"⟩"', 'let ns := (r.nullSpaceArg.replace "\\\\" "\\\\\\\\").replace "\\"" "\\\\\\""\n  s!"⟨{v}, {r.location}, \\"{d}\\", {r.severity}, #[], \\"{ns}\\"⟩"')

with open("bug_bounty_web3.lean", "w") as f:
    f.write(content)
