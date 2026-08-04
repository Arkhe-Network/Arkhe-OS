with open("bug_bounty_web3.lean", "r") as f:
    content = f.read()

old_str = """theorem Fx.mul_error_bound (a b : Fx) :
    0 ≤ a.raw * b.raw - (Fx.mul a b).raw * Fx.SCALE ∧
    a.raw * b.raw - (Fx.mul a b).raw * Fx.SCALE < Fx.SCALE := by
  simp [Fx.mul, Fx.SCALE]; omega"""

new_str = """theorem Fx.mul_error_bound (a b : Fx) :
    0 ≤ a.raw * b.raw - (Fx.mul a b).raw * Fx.SCALE ∧
    a.raw * b.raw - (Fx.mul a b).raw * Fx.SCALE < Fx.SCALE := by
  simp [Fx.mul, Fx.SCALE]
  have h := Int.ediv_add_emod (a.raw * b.raw) Fx.SCALE
  omega"""

content = content.replace(old_str, new_str)
with open("bug_bounty_web3.lean", "w") as f:
    f.write(content)
