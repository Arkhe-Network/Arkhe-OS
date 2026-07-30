package com.cathedral.agi.safety

class SafetyEngine {
    fun isSafe(action: FloatArray, targetId: String, force: Float): Boolean {
        val fragile = listOf("cup", "bottle", "vase", "glass").contains(targetId.lowercase())
        if (fragile && force > 1.0f) return false
        return action.all { it in -1.0f..1.0f }
    }
}