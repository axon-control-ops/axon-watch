package com.axon.vaxon.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.axon.vaxon.BuildConfig
import com.axon.vaxon.net.DeviceEnrollmentClient
import kotlinx.coroutines.launch

@Composable
fun EnrollmentScreen() {
    val scope = rememberCoroutineScope()
    val client = remember { DeviceEnrollmentClient(BuildConfig.CONTROL_PLANE_BASE_URL) }
    var deviceLabel by remember { mutableStateOf("android-companion") }
    var status by remember { mutableStateOf("Not enrolled") }
    var deviceId by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Device enrollment", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Pair this companion with the control plane. Revocation immediately disarms background wake.",
            style = MaterialTheme.typography.bodyMedium,
        )
        OutlinedTextField(
            value = deviceLabel,
            onValueChange = { deviceLabel = it },
            label = { Text("Device label") },
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            onClick = {
                scope.launch {
                    status = "Enrolling…"
                    runCatching {
                        client.enroll(
                            label = deviceLabel,
                            platform = "android",
                            capabilities = listOf("wake.local", "converse", "briefing", "tts"),
                        )
                    }.onSuccess { enrolled ->
                        deviceId = enrolled.deviceId
                        status = "Enrolled: ${enrolled.deviceId}"
                    }.onFailure { err ->
                        status = "Enroll failed: ${err.message}"
                    }
                }
            },
        ) { Text("Enroll") }
        Button(
            enabled = !deviceId.isNullOrBlank(),
            onClick = {
                val id = deviceId ?: return@Button
                scope.launch {
                    status = "Revoking…"
                    runCatching { client.revoke(id) }
                        .onSuccess { status = "Revoked: $id"; deviceId = null }
                        .onFailure { err -> status = "Revoke failed: ${err.message}" }
                }
            },
        ) { Text("Revoke") }
        Text(status, style = MaterialTheme.typography.bodySmall)
    }
}
