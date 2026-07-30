package com.cathedral.agi.memory

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.google.gson.Gson

class EpisodicMemory(context: Context) {
    private val dbHelper = MemoryDBHelper(context)
    private val gson = Gson()

    fun store(state: FloatArray, action: FloatArray, target: String) {
        val db = dbHelper.writableDatabase
        val values = android.content.ContentValues().apply {
            put("state_vector", state.joinToString(","))
            put("action_vector", action.joinToString(","))
            put("target", target)
            put("timestamp", System.currentTimeMillis())
        }
        db.insert("memories", null, values)
        db.close()
    }

    fun recall(query: FloatArray, topK: Int = 5): List<Memory> {
        // Placeholder: linear search. For production, use FAISS or sqlite-vss.
        val db = dbHelper.readableDatabase
        val cursor = db.query("memories", null, null, null, null, null, "timestamp DESC", topK.toString())
        val memories = mutableListOf<Memory>()
        while (cursor.moveToNext()) {
            val state = cursor.getString(cursor.getColumnIndexOrThrow("state_vector")).split(",").map { it.toFloat() }.toFloatArray()
            val action = cursor.getString(cursor.getColumnIndexOrThrow("action_vector")).split(",").map { it.toFloat() }.toFloatArray()
            val target = cursor.getString(cursor.getColumnIndexOrThrow("target"))
            memories.add(Memory(state, action, target))
        }
        cursor.close()
        db.close()
        return memories
    }

    inner class MemoryDBHelper(context: Context) : SQLiteOpenHelper(context, "episodic.db", null, 1) {
        override fun onCreate(db: SQLiteDatabase) {
            db.execSQL("CREATE TABLE memories (id INTEGER PRIMARY KEY, state_vector TEXT, action_vector TEXT, target TEXT, timestamp INTEGER)")
        }
        override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {}
    }

    data class Memory(val state: FloatArray, val action: FloatArray, val target: String)
}