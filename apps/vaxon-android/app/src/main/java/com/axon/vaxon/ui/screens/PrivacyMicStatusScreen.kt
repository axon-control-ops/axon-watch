package com.axon.vaxon.ui.screens

import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.axon.vaxon.wake.WakeWordForegroundService

@Composable
fun PrivacyMicStatusScreen() {
    val context = LocalContext.current
    var listening by remember { mutableStateOf(false) }
    var muted by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Privacy / mic status", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Pre-wake audio stays in a local ring buffer and is never uploaded. " +
                "Mute disarms capture without leaving the foreground service.",
            style = MaterialTheme.typography.bodyMedium,
        )
        Text("Listening: ${if (listening) "armed" else "stopped"}")
        Text("Privacy mute: ${if (muted) "ON" else "off"}")
        Button(
            onClick = {
                context.startForegroundService(
                    Intent(context, WakeWordForegroundService::class.java).apply {
                        action = WakeWordForegroundService.ACTION_START
                    },
                )
                listening = true
                muted = false
            },
        ) { Text("Start wake service") }
        Button(
            onClick = {
                context.startService(
                    Intent(context, WakeWordForegroundService::class.java).apply {
                        action = WakeWordForegroundService.ACTION_STOP
                    },
                )
                listening = false
                muted = false
            },
        ) { Text("Stop wake service") }
        Button(
            enabled = listening,
            onClick = {
                muted = !muted
                context.startService(
                    Intent(context, WakeWordForegroundService::class.java).apply {
                        action = if (muted) {
                            WakeWordForegroundService.ACTION_MUTE
                        } else {
                            WakeWordForegroundService.ACTION_UNMUTE
                        }
                    },
                )
            },
        ) { Text(if (muted) "Unmute mic" else "Privacy mute") }
    }
}
