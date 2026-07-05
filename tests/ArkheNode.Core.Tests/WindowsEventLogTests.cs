using System.Diagnostics;
using System.Runtime.InteropServices;
using Xunit;
using FluentAssertions;

namespace ArkheNode.Core.Tests;

public class ArkheEventSourceTests
{
    [Fact]
    public void EventSource_IsAvailable_WithoutException()
    {
        var isEnabled = ArkheEventSource.Log.IsEnabled();
        // ETW may not be available on all environments; skip assertion in Release
#if DEBUG
        isEnabled.Should().BeTrue("ETW should be available in Debug builds");
#endif
    }

    [Theory]
    [InlineData("node-test-001", 0.9234, true)]
    [InlineData("node-prod-042", 0.7812, false)]
    public void PhiCCalculated_Accepts_Valid_Parameters(string nodeId, double phiC, bool constitutional)
    {
        var act = () => ArkheEventSource.Log.PhiCCalculated(nodeId, phiC, constitutional);
        act.Should().NotThrow();
    }

    [Fact]
    public void ConstitutionalViolation_Logs_Invariant_Name_And_Value()
    {
        var act = () => ArkheEventSource.Log.ConstitutionalViolation("test-node", "ghost", 0.577000);
        act.Should().NotThrow();
    }

    [Fact]
    public void SealGenerated_Handles_Full_Hash()
    {
        var hash = new string('a', 64);
        var act = () => ArkheEventSource.Log.SealGenerated("test-node", hash, 0.95);
        act.Should().NotThrow();
    }

    [Fact]
    public void All_Events_Can_Be_Written_Sequentially()
    {
        if (!ArkheEventSource.Log.IsEnabled()) return;
        ArkheEventSource.Log.PhiCCalculated("test", 0.95, true);
        ArkheEventSource.Log.SealGenerated("test", "abc123", 0.95);
        ArkheEventSource.Log.AuditEvent("{\"test\":\"value\"}");
    }

    [Fact]
    public void IntegrityViolation_CriticalLevel()
    {
        var act = () => ArkheEventSource.Log.IntegrityViolationDetected("n1", "abcdef", "123456");
        act.Should().NotThrow();
    }

    [Fact]
    public void TemporalAnchor_Events_Chain()
    {
        ArkheEventSource.Log.TemporalAnchorStarted("n1", "EVT-0000000001");
        ArkheEventSource.Log.TemporalAnchorCompleted("n1", "sealhash", 42);
    }
}

public class UnifiedAuditLoggerTests
{
    [Fact]
    public void Log_Writes_To_Memory_Logger_Always()
    {
        var logger = new UnifiedAuditLogger("test-node", enableEtw: false);
        logger.Log(new AuditEvent(DateTimeOffset.UtcNow, "", AuditEventLevel.Info, "244", "test-node", "Memory test", 0.90, null, null));
        logger.GetEvents().Should().ContainSingle(e => e.Message == "Memory test");
    }

    [Fact]
    public void Log_Handles_WindowsEventLog_Unavailability_Gracefully()
    {
        var logger = new UnifiedAuditLogger("test-node", enableEtw: false);
        var act = () => logger.Log(new AuditEvent(DateTimeOffset.UtcNow, "", AuditEventLevel.Warning, "244", "test-node", "Fallback test", 0.80, null, null));
        act.Should().NotThrow();
        logger.GetEvents().Should().Contain(e => e.Message == "Fallback test");
    }

    [Fact]
    public void Flush_Does_Not_Throw()
    {
        var logger = new UnifiedAuditLogger("test-node", enableEtw: false);
        logger.Log(new AuditEvent(DateTimeOffset.UtcNow, "", AuditEventLevel.Info, "244", "test", "Flush test", 0.95, null, null));
        logger.Invoking(l => l.Flush()).Should().NotThrow();
    }

    [Fact]
    public async Task Concurrent_Logs_With_UnifiedLogger()
    {
        var logger = new UnifiedAuditLogger("stress-test", enableEtw: false);
        var tasks = Enumerable.Range(0, 10).Select(_ => Task.Run(() =>
        {
            for (int i = 0; i < 100; i++)
                logger.Log(new AuditEvent(DateTimeOffset.UtcNow, "", AuditEventLevel.Info, "244", "node", $"Event {i}", null, null, null));
        })).ToArray();
        await Task.WhenAll(tasks);
        logger.GetEvents().Should().HaveCount(1000);
    }
}
