// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

contract CathedralConsensusLedger {
    struct Event {
        string eventType;
        string payload;      // JSON
        uint256 timestamp;
        uint64 policyVersion;
        bytes signature;     // SPHINCS+ signature (large)
    }

    Event[] public events;
    mapping(bytes32 => bool) public recordedHashes;

    event EventRecorded(uint256 indexed eventId, string eventType, uint64 policyVersion);

    function recordEvent(
        string calldata eventType,
        string calldata payload,
        uint64 policyVersion,
        bytes calldata signature
    ) external {
        // Verificar assinatura SPHINCS+ (pode ser off-chain)
        bytes32 hash = keccak256(abi.encodePacked(eventType, payload, block.timestamp, policyVersion));
        require(!recordedHashes[hash], "Event already recorded");
        // Se necessário, valide a assinatura com uma biblioteca externa de SPHINCS+
        // require(validateSphincsPlus(hash, signature, publicKey), "Invalid signature");

        events.push(Event({
            eventType: eventType,
            payload: payload,
            timestamp: block.timestamp,
            policyVersion: policyVersion,
            signature: signature
        }));
        recordedHashes[hash] = true;

        emit EventRecorded(events.length - 1, eventType, policyVersion);
    }
}
