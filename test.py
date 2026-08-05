with open("bug_bounty_web3.lean", "r") as f:
    content = f.read()
if "Nat.succ_pos _" in content:
    print("Found succ_pos _")
if "⟨min (u.val : Int) (2^24 - 1), by omega⟩" in content:
    print("Found proof in Fx")
