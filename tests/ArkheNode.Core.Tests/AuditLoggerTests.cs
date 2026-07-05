using Xunit;
using FluentAssertions;
using ArkheNode.Core;

namespace ArkheNode.Core.Tests;

public class AuditLoggerTests
{
    [Fact]
    public void Log_ShouldPersistEvents()
    {
        var logger = new InMemoryAuditLogger();
        var evt = new AuditEvent(
            DateTimeOffset.UtcNow, "", AuditEventLevel.Constitutional,
            "310", "NODE-1", "Teste", 0.88, null, null);
        logger.Log(evt);

        var events = logger.GetEvents();
        events.Should().ContainSingle();
    }

    [Fact]
    public void GetEvents_WithSinceFilter_ShouldReturnRecent()
    {
        var logger = new InMemoryAuditLogger();
        var old = new AuditEvent(
            DateTimeOffset.UtcNow.AddHours(-1), "", AuditEventLevel.Info,
            "310", "N", "", null, null, null);
        var recent = new AuditEvent(
            DateTimeOffset.UtcNow, "", AuditEventLevel.Constitutional,
            "310", "N", "", 0.9, null, null);
        logger.Log(old);
        logger.Log(recent);

        var filtered = logger.GetEvents(DateTimeOffset.UtcNow.AddMinutes(-10));
        filtered.Should().ContainSingle().Which.PhiC.Should().Be(0.9);
    }

    [Fact]
    public void ViolationLevel_ShouldBeHigherThanInfo()
    {
        ((int)AuditEventLevel.Violation).Should().BeGreaterThan((int)AuditEventLevel.Info);
    }

    [Fact]
    public void AutocideLevel_ShouldBeHighest()
    {
        ((int)AuditEventLevel.Autocide).Should()
            .BeGreaterThan((int)AuditEventLevel.Violation);
        ((int)AuditEventLevel.Autocide).Should()
            .BeGreaterThan((int)AuditEventLevel.Constitutional);
        ((int)AuditEventLevel.Autocide).Should()
            .BeGreaterThan((int)AuditEventLevel.Info);
    }
}
