package com.axon.vaxon.net

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * HTTP client stubs for Continuity VAXON Parity control-plane endpoints.
 * Scaffold only — no auth token plumbing yet.
 */
class DeviceEnrollmentClient(
    baseUrl: String,
    private val http: OkHttpClient = defaultClient(),
) {
    private val root = baseUrl.trimEnd('/')

    data class EnrolledDevice(
        val deviceId: String,
        val label: String,
        val platform: String,
        val status: String,
        val capabilities: List<String>,
    )

    data class ConverseResult(
        val replyText: String,
        val raw: JSONObject,
    )

    data class BriefingResult(
        val summary: String,
        val raw: JSONObject,
    )

    data class TtsResult(
        val contentType: String,
        val bytes: ByteArray,
    )

    suspend fun enroll(
        label: String,
        platform: String = "android",
        capabilities: List<String> = emptyList(),
    ): EnrolledDevice = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("label", label)
            .put("platform", platform)
            .put("capabilities", JSONArray(capabilities))
            .toString()
        val json = postJson("/api/devices/enroll", body)
        EnrolledDevice(
            deviceId = json.getString("device_id"),
            label = json.optString("label", label),
            platform = json.optString("platform", platform),
            status = json.optString("status", "active"),
            capabilities = json.optJSONArray("capabilities").toStringList(),
        )
    }

    suspend fun revoke(deviceId: String): JSONObject = withContext(Dispatchers.IO) {
        postJson("/api/devices/${deviceId.trim()}/revoke", "{}")
    }

    suspend fun listDevices(): List<EnrolledDevice> = withContext(Dispatchers.IO) {
        val json = getJson("/api/devices")
        val items = json.optJSONArray("items") ?: JSONArray()
        buildList {
            for (i in 0 until items.length()) {
                val row = items.getJSONObject(i)
                add(
                    EnrolledDevice(
                        deviceId = row.getString("device_id"),
                        label = row.optString("label"),
                        platform = row.optString("platform"),
                        status = row.optString("status"),
                        capabilities = row.optJSONArray("capabilities").toStringList(),
                    ),
                )
            }
        }
    }

    suspend fun converse(text: String, deviceId: String? = null): ConverseResult =
        withContext(Dispatchers.IO) {
            val payload = JSONObject()
                .put("text", text)
                .put("source", "android_companion")
            if (!deviceId.isNullOrBlank()) payload.put("device_id", deviceId)
            val json = postJson("/api/kairo/converse", payload.toString())
            ConverseResult(
                replyText = json.optString("reply_text", json.optString("text", "")),
                raw = json,
            )
        }

    suspend fun briefing(deviceId: String? = null): BriefingResult = withContext(Dispatchers.IO) {
        val path = if (deviceId.isNullOrBlank()) {
            "/api/briefing"
        } else {
            "/api/briefing?device_id=${deviceId.trim()}"
        }
        val json = getJson(path)
        BriefingResult(
            summary = json.optString("summary", json.optString("briefing", "")),
            raw = json,
        )
    }

    suspend fun tts(text: String): TtsResult = withContext(Dispatchers.IO) {
        val payload = JSONObject().put("text", text).toString()
        val request = Request.Builder()
            .url("$root/api/kairo/tts")
            .post(payload.toRequestBody(JSON_MEDIA))
            .header("Accept", "*/*")
            .build()
        http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw IllegalStateException("TTS failed HTTP ${response.code}")
            }
            val bytes = response.body?.bytes() ?: ByteArray(0)
            TtsResult(
                contentType = response.header("Content-Type") ?: "application/octet-stream",
                bytes = bytes,
            )
        }
    }

    private fun postJson(path: String, body: String): JSONObject {
        val request = Request.Builder()
            .url("$root$path")
            .post(body.toRequestBody(JSON_MEDIA))
            .header("Accept", "application/json")
            .build()
        return executeJson(request)
    }

    private fun getJson(path: String): JSONObject {
        val request = Request.Builder()
            .url("$root$path")
            .get()
            .header("Accept", "application/json")
            .build()
        return executeJson(request)
    }

    private fun executeJson(request: Request): JSONObject {
        http.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IllegalStateException("HTTP ${response.code}: $raw")
            }
            return if (raw.isBlank()) JSONObject() else JSONObject(raw)
        }
    }

    companion object {
        private val JSON_MEDIA = "application/json; charset=utf-8".toMediaType()

        fun defaultClient(): OkHttpClient = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }
}

private fun JSONArray?.toStringList(): List<String> {
    if (this == null) return emptyList()
    return buildList {
        for (i in 0 until length()) {
            add(optString(i))
        }
    }
}
