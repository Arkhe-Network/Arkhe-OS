package com.cathedral.agi.network

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class SlowBrainRequest(val prompt: String, val max_tokens: Int = 100)
data class SlowBrainResponse(val text: String)

class SlowBrainApi {
    private val client = OkHttpClient()
    private val gson = Gson()
    private val apiUrl = "https://your-server.com/v1/chat/completions"

    suspend fun reason(dilemma: String): String? = withContext(Dispatchers.IO) {
        try {
            val requestBody = gson.toJson(SlowBrainRequest(dilemma))
            val body = requestBody.toRequestBody("application/json".toMediaType())
            val request = Request.Builder().url(apiUrl).post(body).build()
            val response = client.newCall(request).execute()
            if (response.isSuccessful) {
                val resp = gson.fromJson(response.body?.string(), SlowBrainResponse::class.java)
                return@withContext resp.text
            } else null
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }
}