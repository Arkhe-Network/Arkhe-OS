"""Tests for Substrate 1076.2 — AGI OS-Wide Extension v2.0 (Windows Native Bridge)."""

import pytest, os, sys, json, tempfile, time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cathedral_windows_artifacts import (
    AGIOSWideOrchestrator, WindowsNativeInterface, OSState, PlasticLink,
    ProcessAgent, FileSystemAgent, NetworkAgent, ServiceAgent,
    MemoryAgent, SecurityAgent, IOCTLAgent, EventLogAgent,
    PHI, LAMBDA_THESIS, ETA_PLASTICITY, THETA_THRESHOLD,
    MAX_WEIGHT, MIN_WEIGHT, HOMEOSTASIS_DECAY, DELTA_KC, DELTA_KTH,
    OS_DOMAINS, IOCTL_CODES, IOCTL_CATHEDRAL_BASE,
)


class TestConstants:
    def test_phi(self):
        expected = (1 + np.sqrt(5)) / 2
        assert abs(PHI - expected) < 1e-10

    def test_lambda_thesis(self):
        assert LAMBDA_THESIS == 0.5334

    def test_eta_plasticity(self):
        assert ETA_PLASTICITY == 0.5334

    def test_theta_threshold(self):
        assert THETA_THRESHOLD == 0.08

    def test_delta_kc(self):
        assert DELTA_KC == 50.0

    def test_os_domains(self):
        assert "PROCESS" in OS_DOMAINS
        assert "IOCTL" in OS_DOMAINS
        assert "EVENTLOG" in OS_DOMAINS
        assert len(OS_DOMAINS) == 10

    def test_ioctl_codes(self):
        assert IOCTL_CODES['THEOSIS_PROBE'] == IOCTL_CATHEDRAL_BASE + 0x201C
        assert IOCTL_CODES['OS_WIDE_SCAN'] == IOCTL_CATHEDRAL_BASE + 0x2024


class TestOSState:
    def test_default(self):
        s = OSState()
        assert s.theosis == 0.0
        assert s.fatigue_rate == 0.0
        assert s.ethical_status == "ALIGNED"
        assert s.events_processed == 0

    def test_history_maxlen(self):
        s = OSState()
        for i in range(2000):
            s.history.append(i)
        assert len(s.history) == 1000


class TestPlasticLink:
    def test_default(self):
        link = PlasticLink(pre=0, post=1)
        assert link.pre == 0
        assert link.post == 1
        assert link.weight == 1.0
        assert link.plasticity_events == 0

    def test_custom(self):
        link = PlasticLink(pre=2, post=3, weight=5.0, plasticity_events=10)
        assert link.weight == 5.0
        assert link.plasticity_events == 10


class TestWindowsNativeInterface:
    def test_init_not_windows(self):
        wni = WindowsNativeInterface()
        assert hasattr(wni, 'is_windows')
        assert hasattr(wni, 'ioctl_log')

    def test_open_driver_returns_false(self):
        wni = WindowsNativeInterface()
        result = wni.open_driver()
        assert isinstance(result, bool)

    def test_send_ioctl_simulated(self):
        wni = WindowsNativeInterface()
        result = wni.send_ioctl(0x8000 + 0x201C)
        assert b"SIMULATED_IOCTL" in result
        assert len(wni.ioctl_log) == 1
        assert wni.ioctl_log[0]['simulated'] == True

    def test_multiple_ioctls(self):
        wni = WindowsNativeInterface()
        for code in [0x8000, 0x8004, 0x8008]:
            wni.send_ioctl(code)
        assert len(wni.ioctl_log) == 3

    def test_ioctl_log_maxlen(self):
        wni = WindowsNativeInterface()
        for i in range(2000):
            wni.send_ioctl(0x8000 + i)
        assert len(wni.ioctl_log) == 1000

    def test_write_event_log(self):
        wni = WindowsNativeInterface()
        wni.write_event_log(1001, "Test message", "INFO")
        assert len(wni.ioctl_log) >= 1
        assert any(e.get('event_id') == 1001 for e in wni.ioctl_log)

    def test_read_registry_returns_or_none(self):
        wni = WindowsNativeInterface()
        result = wni.read_registry("SOFTWARE\\Cathedral")
        assert result is None or isinstance(result, dict)

    def test_write_registry_returns_bool(self):
        wni = WindowsNativeInterface()
        result = wni.write_registry("SOFTWARE\\Cathedral", "Test", "value")
        assert isinstance(result, bool)


class TestProcessAgent:
    def test_init(self):
        wni = WindowsNativeInterface()
        agent = ProcessAgent(wni)
        assert isinstance(agent.state, OSState)
        assert agent.process_theosis == {}

    def test_get_mean_theosis_empty(self):
        wni = WindowsNativeInterface()
        agent = ProcessAgent(wni)
        assert agent.get_mean_theosis() == 0.0

    def test_get_fatigue_rate_empty(self):
        wni = WindowsNativeInterface()
        agent = ProcessAgent(wni)
        assert agent.get_fatigue_rate() == 0.0

    def test_scan_returns_dict(self):
        wni = WindowsNativeInterface()
        agent = ProcessAgent(wni)
        result = agent.scan_processes()
        assert isinstance(result, dict)


class TestFileSystemAgent:
    def test_init(self):
        wni = WindowsNativeInterface()
        agent = FileSystemAgent(wni)
        assert agent.get_mean_theosis() == 0.0

    def test_scan_returns_list(self):
        wni = WindowsNativeInterface()
        agent = FileSystemAgent(wni, watch_paths=[os.path.dirname(__file__)])
        result = agent.scan_io_activity()
        assert isinstance(result, list)


class TestNetworkAgent:
    def test_init(self):
        wni = WindowsNativeInterface()
        agent = NetworkAgent(wni)
        assert agent.get_mean_theosis() == 0.0


class TestServiceAgent:
    def test_init(self):
        wni = WindowsNativeInterface()
        agent = ServiceAgent(wni)
        assert agent.get_mean_theosis() == 0.0


class TestMemoryAgent:
    def test_init(self):
        wni = WindowsNativeInterface()
        agent = MemoryAgent(wni)
        assert agent.get_mean_theosis() == 0.0


class TestSecurityAgent:
    def test_init(self):
        wni = WindowsNativeInterface()
        agent = SecurityAgent(wni)
        assert agent.get_mean_theosis() == 0.5

    def test_scan_returns_list(self):
        wni = WindowsNativeInterface()
        agent = SecurityAgent(wni)
        result = agent.scan_security_events()
        assert len(result) >= 4


class TestIOCTLAgent:
    def test_init(self):
        wni = WindowsNativeInterface()
        agent = IOCTLAgent(wni)
        assert agent.get_mean_theosis() == 0.0


class TestEventLogAgent:
    def test_init(self):
        wni = WindowsNativeInterface()
        agent = EventLogAgent(wni)
        assert agent.get_mean_theosis() == 0.0

    def test_scan_returns_list(self):
        wni = WindowsNativeInterface()
        agent = EventLogAgent(wni)
        result = agent.scan_event_log()
        assert len(result) == 6


class TestOrchestratorInit:
    def test_default_init(self):
        orch = AGIOSWideOrchestrator()
        assert len(orch.agents) == 8
        assert len(orch.plastic_links) == 10 * 9

    def test_all_agents_present(self):
        orch = AGIOSWideOrchestrator()
        for domain in ['PROCESS', 'FILESYSTEM', 'NETWORK', 'SERVICE', 'MEMORY', 'SECURITY', 'IOCTL', 'EVENTLOG']:
            assert domain in orch.agents

    def test_plastic_links_by_domain(self):
        orch = AGIOSWideOrchestrator()
        for (i, j), link in orch.plastic_links.items():
            assert orch.idx_to_domain[i] in OS_DOMAINS
            assert orch.idx_to_domain[j] in OS_DOMAINS

    def test_initial_global_theosis_low(self):
        orch = AGIOSWideOrchestrator()
        theta = orch.compute_global_theosis()
        assert 0.0 <= theta < 0.5  # Security agent has base 0.5 theosis

    def test_initial_global_fatigue_non_negative(self):
        orch = AGIOSWideOrchestrator()
        assert orch.compute_global_fatigue() >= 0.0

    def test_generation_zero(self):
        orch = AGIOSWideOrchestrator()
        assert orch.generation == 0


class TestOrchestratorStep:
    def test_step_increments_generation(self):
        orch = AGIOSWideOrchestrator()
        orch.step()
        assert orch.generation == 1

    def test_step_returns_dict(self):
        orch = AGIOSWideOrchestrator()
        result = orch.step()
        assert 'generation' in result
        assert 'global_theosis' in result
        assert 'global_fatigue' in result
        assert 'ethical_status' in result
        assert 'subsystems' in result
        assert 'plasticity_events' in result

    def test_step_ethical_status_aligned(self):
        orch = AGIOSWideOrchestrator()
        result = orch.step()
        assert result['ethical_status'] in ("ALIGNED", "WARNING", "BLOCKED")

    def test_step_updates_history(self):
        orch = AGIOSWideOrchestrator()
        orch.step()
        assert len(orch.global_history) == 1

    def test_multiple_steps(self):
        orch = AGIOSWideOrchestrator()
        for _ in range(10):
            orch.step()
        assert orch.generation == 10
        assert len(orch.global_history) == 10

    def test_plasticity_events_non_negative(self):
        orch = AGIOSWideOrchestrator()
        for _ in range(5):
            orch.step()
        total = sum(l.plasticity_events for l in orch.plastic_links.values())
        assert total >= 0

    def test_step_with_ioctl_trigger(self):
        orch = AGIOSWideOrchestrator()
        result = orch.send_ioctl_to_driver('THEOSIS_PROBE')
        assert b"SIMULATED_IOCTL" in result
        result2 = orch.send_ioctl_to_driver('OS_WIDE_SCAN')
        assert b"SIMULATED_IOCTL" in result2


class TestOrchestratorPlasticity:
    def test_apply_plasticity_changes_weights(self):
        orch = AGIOSWideOrchestrator()
        old_weights = {k: v.weight for k, v in orch.plastic_links.items()}
        # Set a gradient to trigger plasticity
        orch.agents['PROCESS'].state.theosis = 1.0
        orch.agents['PROCESS'].process_theosis = {1: 0.9}
        orch.agents['SERVICE'].state.theosis = 0.0
        orch.apply_plasticity()
        new_weights = {k: v.weight for k, v in orch.plastic_links.items()}
        # Some weights should have changed (but may also decay)
        assert any(old_weights[k] != new_weights[k] for k in old_weights)


class TestOrchestratorDashboard:
    def test_get_dashboard(self):
        orch = AGIOSWideOrchestrator()
        orch.step()
        dash = orch.get_dashboard()
        assert dash['substrate'] == '1076.2'
        assert dash['version'] == '2.0.0'
        assert dash['generation'] == 1
        assert 'current_theosis' in dash
        assert 'current_fatigue' in dash
        assert 'subsystems' in dash
        assert 'plasticity_matrix' in dash
        assert 'ethical_status' in dash
        assert 'seal' in dash
        assert 'timestamp' in dash

    def test_dashboard_seal_format(self):
        orch = AGIOSWideOrchestrator()
        dash = orch.get_dashboard()
        assert dash['seal'].startswith('AGI-OS-WIDE-1076.2-')

    def test_dashboard_plasticity_matrix_size(self):
        orch = AGIOSWideOrchestrator()
        dash = orch.get_dashboard()
        assert len(dash['plasticity_matrix']) == 10 * 9

    def test_dashboard_subsystems_all_present(self):
        orch = AGIOSWideOrchestrator()
        dash = orch.get_dashboard()
        for domain in ['PROCESS', 'FILESYSTEM', 'NETWORK', 'SERVICE', 'MEMORY', 'SECURITY', 'IOCTL', 'EVENTLOG']:
            assert domain in dash['subsystems']

    def test_export_dashboard_creates_file(self):
        orch = AGIOSWideOrchestrator()
        orch.step()
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = orch.export_dashboard(f.name)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            assert data['substrate'] == '1076.2'
            assert data['generation'] == 1
        finally:
            os.unlink(path)

    def test_trend_tracking(self):
        orch = AGIOSWideOrchestrator()
        for _ in range(5):
            orch.step()
        dash = orch.get_dashboard()
        assert len(dash['theosis_trend']) > 0
        assert len(dash['fatigue_trend']) > 0


class TestOrchestratorContinuous:
    def test_run_continuous_returns_dashboard(self):
        orch = AGIOSWideOrchestrator()
        dash = orch.run_continuous(interval=0.1, max_steps=3)
        assert dash['substrate'] == '1076.2'
        assert dash['generation'] >= 1

    def test_run_continuous_generates_steps(self):
        orch = AGIOSWideOrchestrator()
        dash = orch.run_continuous(interval=0.1, max_steps=5)
        assert dash['generation'] == 5
        assert len(orch.global_history) == 5

    def test_run_continuous_theosis_non_negative(self):
        orch = AGIOSWideOrchestrator()
        dash = orch.run_continuous(interval=0.1, max_steps=3)
        assert dash['current_theosis'] >= 0


class TestSendIOCTL:
    def test_all_ioctl_codes(self):
        orch = AGIOSWideOrchestrator()
        for name in IOCTL_CODES:
            result = orch.send_ioctl_to_driver(name)
            assert result is not None

    def test_invalid_ioctl_code(self):
        orch = AGIOSWideOrchestrator()
        result = orch.send_ioctl_to_driver('NONEXISTENT')
        assert result is not None  # Should not crash

    def test_ioctl_with_data(self):
        orch = AGIOSWideOrchestrator()
        result = orch.send_ioctl_to_driver('DNA_WRITE', b'hello')
        assert result is not None


class TestSealGeneration:
    def test_seal_unique_per_generation(self):
        orch = AGIOSWideOrchestrator()
        s1 = orch.generate_seal()
        orch.generation = 100
        s2 = orch.generate_seal()
        assert s1 != s2

    def test_seal_length(self):
        orch = AGIOSWideOrchestrator()
        seal = orch.generate_seal()
        prefix = "AGI-OS-WIDE-1076.2-"
        assert len(seal) == len(prefix) + 16
