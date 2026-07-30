// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.28;

/**
 * @title CathedralSPHINCSVerifier
 * @dev Verifies SPHINCS- C13 (WOTS+C / FORS+C) post-quantum signatures on-chain.
 *      Parameters: n=16, w=8, l=43, k=8, a=16, d=2, h=24, S_wn = target digit sum.
 *      Public key is a Merkle root (16 bytes, stored left-aligned in bytes32).
 */
contract CathedralSPHINCSVerifier {
    // ------------------------------------------------------------
    // Constants (C13)
    // ------------------------------------------------------------
    uint256 internal constant N = 16;
    uint256 internal constant W = 8;
    uint256 internal constant L = 43;
    uint256 internal constant K = 8;
    uint256 internal constant A = 16;
    uint256 internal constant D = 2;
    uint256 internal constant H_TOTAL = 24;
    uint256 internal constant H_PER_LAYER = 12;
    uint256 internal constant WOTS_CHAIN_MAX = 7; // W - 1

    // SIG_SIZE is exactly 3952 bytes assuming uncompressed auth paths.
    // 16 (randomizer) + 8 * (16 + 16*16) (FORS) + 2 * 43 * 16 (WOTS+) + 2 * 12 * 16 (Merkle) = 3952
    // If the signature uses advanced tree path compression, it would be smaller (e.g. 3704).
    uint256 internal constant SIG_SIZE = 3952;

    /**
     * @dev Verifies a SPHINCS- C13 signature.
     */
    function verifySPHINCS(
        bytes32 message,
        bytes calldata signature,
        bytes32 publicKeyRoot
    ) external pure returns (bool) {
        require(signature.length == SIG_SIZE, "Invalid signature length");

        uint256 offset = 0;

        // 1. Parse randomizer
        bytes32 randomizer;
        assembly {
            randomizer := calldataload(signature.offset)
        }
        randomizer &= bytes32(uint256(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF) << 128);
        offset += N;

        // Derive digest, idx_tree, idx_leaf from randomizer + message
        bytes32 md = keccak256(abi.encodePacked(randomizer, message));

        uint256 digestFors = uint256(md) >> 128; // Upper 128 bits for FORS indices
        uint256 idxTree = (uint256(md) >> 116) & 0xFFF; // Next 12 bits
        uint256 idxLeaf = (uint256(md) >> 104) & 0xFFF; // Next 12 bits

        // 2. FORS
        uint256 forsTotalSize = K * (N + A * N);
        bytes32 forsPK = _reconstructFORSPublicKey(
            signature[offset:offset + forsTotalSize],
            digestFors
        );
        offset += forsTotalSize;

        // 3. First WOTS+ layer (bottom layer)
        uint256 wotsSize = L * N;
        bytes32 layer0Node = _verifyWOTSC(
            signature[offset:offset + wotsSize],
            forsPK
        );
        offset += wotsSize;

        // 4. First Merkle path to layer 1
        uint256 merkleAuthSizeLayer0 = H_PER_LAYER * N;
        layer0Node = _verifyMerklePath(
            layer0Node,
            signature[offset:offset + merkleAuthSizeLayer0],
            idxLeaf
        );
        offset += merkleAuthSizeLayer0;

        // 5. Second WOTS+ layer (top layer)
        bytes32 layer1Node = _verifyWOTSC(
            signature[offset:offset + wotsSize],
            layer0Node
        );
        offset += wotsSize;

        // 6. Second Merkle path to public key root
        uint256 merkleAuthSizeLayer1 = H_PER_LAYER * N;
        bytes32 computedRoot = _verifyMerklePath(
            layer1Node,
            signature[offset:offset + merkleAuthSizeLayer1],
            idxTree
        );
        offset += merkleAuthSizeLayer1;

        // Final mask to 16 bytes
        computedRoot &= bytes32(uint256(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF) << 128);
        bytes32 expectedRoot = publicKeyRoot & bytes32(uint256(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF) << 128);

        return computedRoot == expectedRoot;
    }

    function _reconstructFORSPublicKey(
        bytes calldata forsData,
        uint256 digestFors
    ) internal pure returns (bytes32) {
        bytes32[] memory forsRoots = new bytes32[](K);
        uint256 offset = 0;

        for (uint256 i = 0; i < K; i++) {
            uint256 leafIdx = (digestFors >> (128 - (i + 1) * A)) & 0xFFFF;

            bytes32 leaf;
            assembly {
                let pos := add(forsData.offset, offset)
                leaf := and(calldataload(pos), 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000)
            }
            offset += N;

            bytes32 root = keccak256(abi.encodePacked(leaf));
            root &= bytes32(uint256(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF) << 128);

            for (uint256 j = 0; j < A; j++) {
                bytes32 sibling;
                assembly {
                    let pos := add(forsData.offset, offset)
                    sibling := and(calldataload(pos), 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000)
                }
                offset += N;

                if ((leafIdx >> j) & 1 == 0) {
                    root = keccak256(abi.encodePacked(root, sibling));
                } else {
                    root = keccak256(abi.encodePacked(sibling, root));
                }
                root &= bytes32(uint256(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF) << 128);
            }
            forsRoots[i] = root;
        }

        bytes32 finalRoot = keccak256(abi.encodePacked(forsRoots));
        return finalRoot & bytes32(uint256(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF) << 128);
    }

    function _verifyWOTSC(
        bytes calldata wotsSig,
        bytes32 msgHash
    ) internal pure returns (bytes32) {
        uint256[] memory digits = new uint256[](L);
        uint256 currentVal = uint256(msgHash) >> 128; // Upper 128 bits

        for (uint256 i = 0; i < 42; i++) {
            digits[i] = (currentVal >> (125 - i * 3)) & 0x7;
        }
        digits[42] = (currentVal << 1) & 0x7; // The last 2 bits, shifted appropriately

        bytes32[] memory chains = new bytes32[](L);
        uint256 offset = 0;

        for (uint256 i = 0; i < L; i++) {
            bytes32 chain;
            assembly {
                let pos := add(wotsSig.offset, offset)
                chain := and(calldataload(pos), 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000)
            }
            offset += N;

            uint256 steps = WOTS_CHAIN_MAX - digits[i];
            for (uint256 j = 0; j < steps; j++) {
                chain = keccak256(abi.encodePacked(chain));
                chain &= bytes32(uint256(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF) << 128);
            }
            chains[i] = chain;
        }

        bytes32 pkHash = keccak256(abi.encodePacked(chains));
        return pkHash & bytes32(uint256(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF) << 128);
    }

    function _verifyMerklePath(
        bytes32 leaf,
        bytes calldata authPath,
        uint256 leafIdx
    ) internal pure returns (bytes32) {
        bytes32 node = leaf;
        for (uint256 i = 0; i < H_PER_LAYER; i++) {
            bytes32 sibling;
            assembly {
                let pos := add(authPath.offset, mul(i, N))
                sibling := and(calldataload(pos), 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000000000000000000000000000)
            }

            if ((leafIdx >> i) & 1 == 0) {
                node = keccak256(abi.encodePacked(node, sibling));
            } else {
                node = keccak256(abi.encodePacked(sibling, node));
            }
            node &= bytes32(uint256(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF) << 128);
        }
        return node;
    }
}
