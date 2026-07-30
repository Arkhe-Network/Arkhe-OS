import re

def test_617_f_strings():
    file_path = "substrates/617-QUANTUM-TELEPORT/substrato_617_quantum_teleport.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert not re.search(r'\bf(["\'])', content), "f-strings found!"

def test_719_f_strings():
    import ast
    with open('substrates/s/719_glosa_240_metacognition/substrato_719_glosa_240_metacognition.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_1114_cathedral_sphincs_verifier_f_strings():
    import ast
    with open('substrates/t/1114_cathedral_sphincs_verifier/substrato_1114_cathedral_sphincs_verifier.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)
def test_4004_b20_base_bridge_f_strings():
    import ast
    with open('substrates/t/4004_b20_base_bridge/canonizer.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr), "f-string found in canonizer.py"

def test_825_f_strings():
    import ast
    with open('substrates/t/825_parametric_memory_engine/substrato_825_parametric_memory_engine.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_841_f_strings():
    import ast
    with open('substrates/t/841_web3_ontology_bridge/substrato_841_web3_ontology_bridge.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_870_f_strings():
    import ast
    with open('substrates/t/870_blockchain_z_glm/substrato_870_blockchain_z_glm.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_870_g_f_strings():
    import glob
    for filepath in glob.glob("substrates/t/870_g_arkhe_http_gateway/*.py"):
        with open(filepath, 'r') as f:
            content = f.read()
            assert "f\"" not in content, f"f-strings are strictly prohibited in the codebase. Found in {filepath}"

def test_pvac_f_strings_896_telco_nfv_bridge():
    import ast
    with open('substrates/t/896_telco_nfv_bridge/substrato_896_telco_nfv_bridge.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_pvac_f_strings_898_899_900():
    import os
    files_to_check = [
        "substrates/t/898_kolmogorov_weight/substrato_898.py",
        "substrates/t/899_lightclock_harmony/substrato_899.py",
        "substrates/t/900_peptide_saas/substrato_900.py",
    ]
    for file in files_to_check:
        with open(file, 'r') as f:
            content = f.read()
            assert 'f"' not in content, f"Found f-string in {file}"
            assert "f'" not in content, f"Found f-string in {file}"

def test_pvac_f_strings_905_909():
    import os
    files_to_check = [
        "substrates/t/905_crops_local_ai_stack/substrato_905_crops_local_ai_stack.py",
        "substrates/t/906_lucebox_inference_engine/substrato_906_lucebox_inference_engine.py",
        "substrates/t/907_voxterm_audio_privacy/substrato_907_voxterm_audio_privacy.py",
        "substrates/t/908_leanstral_fv_bridge/substrato_908_leanstral_fv_bridge.py",
        "substrates/t/909_zk_remote_llm/substrato_909_zk_remote_llm.py",
    ]
    for file in files_to_check:
        with open(file, 'r') as f:
            content = f.read()
            assert 'f"' not in content, f"Found f-string in {file}"
def test_substrate_918_f_strings():
    with open("substrates/t/918_qemu_orchestration/substrate_918_qemu_orchestration.py", "r") as f:
        content = f.read()
    assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."
def test_substrate_919_f_strings():
    with open("substrates/t/919_omni_substrate/substrato_919_omni_substrate.py", "r") as f:
        content = f.read()
    assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."
def test_substrate_926_f_strings():
    with open("substrates/t/926_chrome_devtools_mcp_bridge/substrato_926_chrome_devtools_mcp_bridge.py", "r") as f:
        content = f.read()
    assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."
def test_substrate_929_f_strings():
    import os
    file_path = "substrates/t/929_arkhe_android_os_bridge/substrato_929_arkhe_android_os_bridge.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
        assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."

def test_substrate_989_w_f_strings():
    import os
    file_path = "substrates/t/989_unified_orchestrator/substrato_989_w_unified_orchestrator.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
        assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."

def test_substrate_989_v_f_strings():
    import os
    file_path = "substrates/t/989_fair_metrics_dashboard/substrato_989_v_fair_metrics_dashboard.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
        assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."

def test_substrate_989_y_f_strings():
    import os
    file_path = "substrates/t/989_desci_nodes_bridge/substrato_989_y_desci_nodes_bridge.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
        assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."

def test_substrate_931_f_strings():
    import os
    file_path = "substrates/t/931_interfold_coordination_bridge/substrato_931_interfold_coordination_bridge.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
        assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."

def test_substrate_261_f_strings():
    """Verify that Substrate 261 does not contain f-strings."""
    script_path = "substrates/t/261_arkhe_brasil_finance/substrato_261_arkhe_brasil_finance.py"
    with open(script_path, "r") as f:
        content = f.read()
        assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."

def test_substrate_945_f_strings():
    import os
    file_path = "substrates/t/945_openmdw_fcr_bridge/substrato_945_openmdw_fcr_bridge.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
        assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."

def test_substrate_958_f_strings():
    import os
    file_path = "substrates/t/958_clarity_gate/substrato_958_clarity_gate.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
        assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."

def test_no_f_strings_972_1():
    import re
    with open("substrates/t/972_1_nostr_tor_ipfs_bridge/substrato_972_1_nostr_tor_ipfs_bridge.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_973():
    import re
    with open("substrates/t/973_nostr_relay/substrato_973_nostr_relay.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_974():
    import re
    with open("substrates/t/974_tor_mesh/substrato_974_tor_mesh.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_975():
    import re
    with open("substrates/t/975_ipfs_core/substrato_975_ipfs_core.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_970():
    import re
    with open("substrates/t/970_enterprise_mind/substrato_970_enterprise_mind.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_971():
    import re
    with open("substrates/t/971_self_reflexive_cathedral/substrato_971_self_reflexive.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_972():
    import re
    with open("substrates/t/972_internet_cathedral/substrato_972_internet_cathedral.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_972_1():
    import re
    with open("substrates/t/972_1_nostr_tor_ipfs_bridge/substrato_972_1_nostr_tor_ipfs_bridge.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_973():
    import re
    with open("substrates/t/973_nostr_relay/substrato_973_nostr_relay.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_974():
    import re
    with open("substrates/t/974_tor_mesh/substrato_974_tor_mesh.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_975():
    import re
    with open("substrates/t/975_ipfs_core/substrato_975_ipfs_core.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_970():
    import re
    with open("substrates/t/970_enterprise_mind/substrato_970_enterprise_mind.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_971():
    import re
    with open("substrates/t/971_self_reflexive_cathedral/substrato_971_self_reflexive.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_no_f_strings_972():
    import re
    with open("substrates/t/972_internet_cathedral/substrato_972_internet_cathedral.py", "r") as f:
        content = f.read()
    assert re.search(r"f['\"]", content) is None

def test_substrate_989_f_strings():
    import os
    file_path = "substrates/t/989_passport_gateway/substrato_989_passport_gateway.py"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            content = f.read()
        assert 'f"' not in content and "f'" not in content, "F-strings are strictly forbidden in Python canonizers."

def test_989_y_3_f_strings():
    import os
    import re
    file_path = os.path.abspath('substrates/t/989_y_3_full_100t_orchestrator/substrato_989_y_3_full_100t_orchestrator.py')
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    assert re.search(r'\bf["\']', content) is None, f"Found f-strings in {file_path}"

def test_998_f_strings():
    import os
    import re
    # Check that f-strings are strictly forbidden in the source
    path = "substrates/t/998_recursive_mutation_engine/recursive_mutation_engine.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "f'" not in content and 'f"' not in content, "f-strings are strictly forbidden"

    path2 = "substrates/t/998_recursive_mutation_engine/substrato_998_recursive_mutation_engine.py"
    with open(path2, "r", encoding="utf-8") as f:
        content = f.read()
    assert "f'" not in content and 'f"' not in content, "f-strings are strictly forbidden"

def test_f_strings_substrate_1007():
    import os
    canonizer = "substrates/t/1007_jules_training/substrato_1007_jules_training.py"
    assert os.path.exists(canonizer)
    with open(canonizer, "r") as f:
        content = f.read()
    assert 'f"' not in content
    assert "f'" not in content

def test_f_strings_substrate_1008_1():
    import os
    canonizer = "substrates/t/1008_1_recursive_mutation_engine_v2/substrato_1008_1_recursive_mutation_engine_v2.py"
    assert os.path.exists(canonizer)
    with open(canonizer, "r") as f:
        content = f.read()
    assert 'f"' not in content
    assert "f'" not in content


def test_no_f_strings_substrate_951():
    import subprocess
    import glob
    import os
    path = "substrates/t/951*/*"
    files_to_check = glob.glob(path)

    if not files_to_check:
        return

    for file in files_to_check:
        if file.endswith(".py"):
            with open(file, "r") as f:
                content = f.read()
            import re
            lines = content.split('\n')
            for line in lines:
                if re.search(r'f["\']', line) and not "# noqa: FS002" in line:
                    assert False, f"f-string found in {file}: {line}"


def test_no_f_strings_substrate_954_1():
    import subprocess
    import glob
    import os
    path = "substrates/t/954_1/*"
    files_to_check = glob.glob(path)

    if not files_to_check:
        return

    for file in files_to_check:
        if file.endswith(".py"):
            with open(file, "r") as f:
                content = f.read()
            import re
            lines = content.split('\n')
            for line in lines:
                if re.search(r'f["\']', line) and not "# noqa: FS002" in line:
                    assert False, f"f-string found in {file}: {line}"


def test_no_f_strings_substrate_955_1():
    import subprocess
    import glob
    import os
    path = "substrates/t/955_1/*"
    files_to_check = glob.glob(path)

    if not files_to_check:
        return

    for file in files_to_check:
        if file.endswith(".py"):
            with open(file, "r") as f:
                content = f.read()
            import re
            lines = content.split('\n')
            for line in lines:
                if re.search(r'f["\']', line) and not "# noqa: FS002" in line:
                    assert False, f"f-string found in {file}: {line}"


def test_no_f_strings_substrate_972_2():
    import subprocess
    import glob
    import os
    path = "substrates/t/972_2/*"
    files_to_check = glob.glob(path)

    if not files_to_check:
        return

    for file in files_to_check:
        if file.endswith(".py"):
            with open(file, "r") as f:
                content = f.read()
            import re
            lines = content.split('\n')
            for line in lines:
                if re.search(r'f["\']', line) and not "# noqa: FS002" in line:
                    assert False, f"f-string found in {file}: {line}"


def test_no_f_strings_substrate_1018():
    import subprocess
    import glob
    import os
    path = "substrates/t/1018*/*"
    files_to_check = glob.glob(path)

    if not files_to_check:
        return

    for file in files_to_check:
        if file.endswith(".py"):
            with open(file, "r") as f:
                content = f.read()
            import re
            lines = content.split('\n')
            for line in lines:
                if re.search(r'f["\']', line) and not "# noqa: FS002" in line:
                    assert False, f"f-string found in {file}: {line}"

def test_no_f_strings_substrate_989_x_v3():
    import subprocess
    result = subprocess.run(["python3", "tests/regex_f_strings.py", "substrates/t/989_x_v3*/*"], capture_output=True, text=True)
    assert result.returncode == 0

def test_no_f_strings_substrate_989_x_v3():
    import subprocess
    import glob
    import os
    path = "substrates/t/989_x_v3*/*"
    files_to_check = glob.glob(path)

    if not files_to_check:
        return

    for file in files_to_check:
        if file.endswith(".py"):
            with open(file, "r") as f:
                content = f.read()
            import re
            lines = content.split('\n')
            for line in lines:
                if re.search(r'f["\']', line) and not "# noqa: FS002" in line:
                    assert False, f"f-string found in {file}: {line}"

def test_no_f_strings_substrate_1018_1():
    import subprocess
    import glob
    import os
    path = "substrates/t/1018_1*/*"
    files_to_check = glob.glob(path)

    if not files_to_check:
        return

    for file in files_to_check:
        if file.endswith(".py"):
            with open(file, "r") as f:
                content = f.read()
            import re
            lines = content.split('\n')
            for line in lines:
                if re.search(r'f["\']', line) and not "# noqa: FS002" in line:
                    assert False, f"f-string found in {file}: {line}"

def test_substrate_1040_canonizer_f_strings():
    import re
    with open("substrato_1040_hermes_bridge.py", "r", encoding="utf-8") as f:
        content = f.read()

    # We only care about f-strings in the canonizer.
    f_strings = re.findall(r'f["\']', content)
    assert not f_strings, "O canonizador 1040 não deve conter f-strings (f\"...\")."

def test_1038_1_f_strings():
    import subprocess
    result = subprocess.run(
        ["python3", "substrates/t/1038_1_continuous_fuzzer/substrato_1038_1.py"],
        capture_output=True,
        text=True,
        check=True
    )
    assert 'f"' not in open('substrates/t/1038_1_continuous_fuzzer/substrato_1038_1.py').read()
    assert "f'" not in open('substrates/t/1038_1_continuous_fuzzer/substrato_1038_1.py').read()

def test_1042_f_strings():
    import os
    canonizer_path = os.path.abspath('substrates/t/1042_rbb_cathedral_bridge/substrato_1042_rbb_cathedral_bridge.py')
    with open(canonizer_path, 'r', encoding='utf-8') as f:
        code = f.read()
    assert 'f"' not in code and "f'" not in code, "Canonizers must not contain f-strings"

def test_substrate_1047_f_strings():
    import re
    with open('src/arkhe/substrates/t/1047_twin_wallet/substrato_1047_twin_wallet_canonizer.py', 'r') as f:
        content = f.read()
    assert not re.search(r'f[\"\']', content)

def test_substrate_1051_no_f_strings():
    import os
    import re
    script_path = os.path.join("substrates", "t", "1051_asi_ordeal", "substrato_1051_asi_ordeal.py")
    if not os.path.exists(script_path):
        return

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Very simple check for f-strings: f"..." or f'...'
    # If the file has # noqa: FS002 or if it's not a canonizer script, this test might need tuning.
    has_f_strings = re.search(r'f[\"\']', content) is not None
    assert not has_f_strings, f"F-strings found in {script_path}"

def test_substrate_1053_4_f_strings():
    canonizer_path = "substrates/t/1053_4_hamiltonian_temporal_implosion_v5/substrato_1053_4_hamiltonian_temporal_implosion_v5.py"
    import ast
    with open(canonizer_path, "r") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_1064_1_f_strings():
    import ast
    with open('substrates/t/1064_1_meta_extract_continuous/substrato_1064_1_meta_extract_continuous.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_1064_2_f_strings():
    import ast
    with open('substrates/t/1064_2_theosis_paris_dashboard/substrato_1064_2_theosis_paris_dashboard.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_1064_3_f_strings():
    import ast
    with open('substrates/t/1064_3_rbb_bridge_global/substrato_1064_3_rbb_bridge_global.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_1064_4_f_strings():
    import ast
    with open('substrates/t/1064_4_constitution_ai/substrato_1064_4_constitution_ai.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_1065_f_strings():
    with open('substrates/t/1065_arkhe_cathedral_blueprint/substrato_1065_arkhe_cathedral_blueprint.py', 'r') as f:
        content = f.read()
    assert 'f"' not in content and "f'" not in content, "f-strings are strictly forbidden in python canonizers"

def test_1065_f_strings():
    with open('substrates/t/1065_arkhe_cathedral_blueprint/substrato_1065_arkhe_cathedral_blueprint.py', 'r') as f:
        content = f.read()
    assert 'f"' not in content and "f'" not in content, "f-strings are strictly forbidden in python canonizers"

def test_substrate_1066_1_f_strings():
    import ast
    with open("substrates/t/1066_1_fordefi_bridge_orchestrator/substrato_1066_1_fordefi_bridge.py", "r") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr), "F-strings are not allowed in the canonizer"

def test_1068_f_strings():
    import ast
    with open("substrates/t/1068_arkhe_cathedral_master_repo/substrato_1068_arkhe_cathedral_master_repo.py", "r") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr), "F-strings are not allowed in the canonizer"

def test_1077_f_strings():
    import os
    import re

    filepath = os.path.abspath('substrato_1077_goose_cathedral_bridge.py')
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'\bf([\'"])'
    matches = re.findall(pattern, content)
    assert not matches, f"Found f-strings in substrato_1077_goose_cathedral_bridge.py: {matches}"

def test_1079_1080_auto_canonization_engine_f_strings():
    import os
    import re
    file_path = os.path.abspath("substrates/t/1079_1080_auto_canonization_engine/substrato_1079_1080_auto_canonization_engine.py")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    f_string_pattern = re.compile(r'\bf(["\'])')
    matches = f_string_pattern.findall(content)
    assert not matches, f"f-strings found in {file_path}"


def test_8000_headroom_bridge_f_strings():
    file_path = "substrates/t/8000_headroom_bridge/canonizer_8000.py"
    with open(file_path, "rb") as f:
        content = f.read()
    assert not re.search(rb'f([\'"])', content), f"File {file_path} contains f-strings!"

def test_1200_fsi_f_strings():
    import os
    import re
    file_path = "substrates/t/1200_federacao_soberana_inferencia/fsi_canonizer.py"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        f_string_pattern = re.compile(r'\bf(["\'])')
        assert not f_string_pattern.search(content), f"Found f-string in {file_path}"

def test_1082_cathedral_translation_engine_f_strings():
    import os
    import re
    file_path = os.path.abspath("substrates/t/1082_cathedral_translation_engine/substrato_1082_cathedral_translation_engine.py")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    f_string_pattern = re.compile(r'\bf(["\'])')
    matches = f_string_pattern.findall(content)
    assert not matches, f"f-strings found in {file_path}"

def test_1084_moltbook_identity_bridge_f_strings():
    import os
    import re
    file_path = os.path.abspath("substrates/t/1084_moltbook_identity_bridge/substrato_1084_moltbook_identity_bridge.py")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert not re.search(r'\bf(["\'])', content), "f-string found in " + file_path

def test_1088_complex_network_optimization_engine_f_strings():
    import os
    import re
    file_path = os.path.abspath("substrates/t/1088_complex_network_optimization_engine/substrato_1088_complex_network_optimization_engine.py")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert not re.search(r'\bf(["\'])', content), "f-string found in " + file_path

def test_1076_3_f_strings():
    import ast
    with open('substrates/t/1076_3_orchestrator_rsi_loop/substrato_1076_3_orchestrator_rsi_loop.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_1093_f_strings():
    import os
    import re
    file_path = os.path.abspath("substrates/t/1093_universal_architecture_bridge/substrato_1093_universal_architecture_bridge.py")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert not re.search(r'\bf(["\'])', content), "f-string found in " + file_path

def test_1098_f_strings():
    import os
    file_path = os.path.abspath("substrates/t/1098_orchestrator_v5/orchestrator_v5.py")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    import re
    # We use \bf(['"]) to avoid matching strings like 'f"' inside base64 payload
    assert not re.search(r'\bf(["\'])', content), ("Encontrado f-string em %s" % file_path)

def test_1101_f_strings():
    import ast
    with open('substrates/t/1101_hashtree_bridge/substrato_1101_hashtree_bridge.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_1102_rsi_safety_addendum_f_strings():
    import os
    import re
    file_path = os.path.abspath("substrates/t/1102_rsi_safety_addendum/substrato_1102_rsi_safety_addendum.py")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # We use \bf(['"]) to avoid matching strings like 'f"' inside base64 payload
    assert not re.search(r'\bf(["\'])', content), ("Encontrado f-string em %s" % file_path)

def test_1105_cathedral_ui_noesis_f_strings():
    import importlib.util
    import os
    import re
    file_path = os.path.abspath('substrates/t/1105_cathedral_ui_noesis/substrato_1105.py')
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert len(re.findall(r'\bf(["\'])', content)) == 0, "f-strings found in Python canonizer 1105"


def test_1130_episteme_ontology_expansion_no_f_strings():
    import re
    with open('substrates/t/episteme_discourse_detector/substrato_1130_episteme_ontology_expansion.py', 'r') as f:
        content = f.read()
    assert not re.search(r'\bf([\'"\n])', content), "f-strings found in Python canonizer"

    with open('substrates/t/episteme_discourse_detector/episteme_discourse_detector.py', 'r') as f:
        content = f.read()
    assert not re.search(r'\bf([\'"\n])', content), "f-strings found in Python payload"

def test_1113_f_strings():
    import ast
    with open("substrates/t/1113_cathedral_agi_omega_v13/substrato_1113_cathedral_agi_omega_v13.py", "r") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr), "F-strings are not allowed in the canonizer"

def test_1101_qubes_f_strings():
    import ast
    with open('substrates/t/1101_cathedral_qubes_integration/substrato_1101_cathedral_qubes_integration.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_1103_btfs_depin_storage_f_strings():
    import ast
    with open('substrates/t/1103_btfs_depin_storage/substrato_1103_btfs_depin_storage.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_12_9_multi_cut_out_f_strings():
    import ast

    files_to_check = [
        'substrates/t/12_9_multi_cut_out_bft/substrato_12_9_multi_cut_out.py',
        'substrates/t/12_9_multi_cut_out_bft/multi_cut_out_bft.py',
        'substrates/t/12_9_multi_cut_out_bft/classification_enforcement.py'
    ]

    for file_path in files_to_check:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            assert not isinstance(node, ast.JoinedStr), "F-strings are not allowed in %s" % file_path

def test_00_cognitive_kernel_no_f_strings():
    import re
    with open('substrates/t/00_cognitive_kernel/substrato_00_cognitive_kernel.py', 'r', encoding='utf-8') as f:
        content = f.read()
    if re.search(r'\bf(["\'])', content):
        assert False, "Found f-strings in substrato_00_cognitive_kernel.py"

def test_1120_cathedral_blockchain_spec_no_fstrings():
    import re
    with open('substrates/t/cathedral_blockchain_spec/substrato_1120_cathedral_blockchain_spec.py', 'r') as f:
        content = f.read()

    # Simple check for f-strings: look for f"..." or f'...'
    # Use the regex that memory mentioned: \bf(['"])
    pattern = re.compile(r'\bf([\'"])')
    match = pattern.search(content)
    assert match is None, "f-string found in substrato_1120_cathedral_blockchain_spec.py"

def test_2140_7_f_strings():
    file_path = "substrates/t/2140_7_firewall_semantico_temporal/substrato_2140_7.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert not re.search(r'\bf(["\'])', content), "f-strings found!"

def test_319_1_f_strings():
    import ast
    with open('substrates/t/319_1_caster_software/substrato_319_1.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_1300_f_strings():
    import ast
    with open('substrates/t/1300_asi_readiness/canonizer_1300.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr), "f-strings found!"

def test_no_f_strings_1600_cognitive_autonomous_structural():
    import os
    import re

    base_dir = "substrates/t/1600_cognitive_autonomous_structural"
    f_string_pattern = re.compile(r'\bf([\'\"])')

    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    matches = f_string_pattern.findall(content)
                    assert not matches, "Found f-strings in " + file_path + ": " + str(matches)

def test_16_2_zvec_f_strings():
    import os
    import re
    # check that we aren't using f-strings
    target_dir = os.path.join(os.path.dirname(__file__), "substrates", "t", "16_2_zvec")
    f_string_pattern = re.compile(rb'f([\'"])')
    if os.path.exists(target_dir):
        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "rb") as f:
                        content = f.read()
                        assert not f_string_pattern.search(content), "f-string found in {0}".format(file_path)
import ast

def test_3001_f_strings():
    with open('substrates/t/3001_agi_platform_specification/substrato_3001.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_1115_f_strings():
    import ast
    import glob
    for filepath in glob.glob("substrates/t/1115_paxos_usdg_integration/*.py"):
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            assert not isinstance(node, ast.JoinedStr), "f-strings found in {0}!".format(filepath)

def test_265_f_strings():
    import ast
    with open('substrates/t/265_tensorzkp_gpu_daemon_v5_0/substrato_265.py', 'r') as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        assert not isinstance(node, ast.JoinedStr)

def test_canonizer_7001_v2_no_fstrings():
    import re
    import os
    canonizer_path = os.path.join("substrates", "t", "7001_x402_polar_v2", "canonizer_7001.py")
    if os.path.exists(canonizer_path):
        with open(canonizer_path, "r", encoding="utf-8") as f:
            content = f.read()
            # The python file must not contain any f-string
            assert not re.search(r'f["\']', content)
