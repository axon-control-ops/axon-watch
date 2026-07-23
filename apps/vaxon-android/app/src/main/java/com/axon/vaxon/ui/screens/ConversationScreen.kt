package com.axon.vaxon.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.unit.dp

@Composable
fun ConversationScreen() {
    val primary = MaterialTheme.colorScheme.primary
    val tertiary = MaterialTheme.colorScheme.tertiary

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Conversation", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Orb placeholder — wire converse + TTS after enrollment evidence gates pass.",
            style = MaterialTheme.typography.bodyMedium,
        )
        Box(
            modifier = Modifier.weight(1f),
            contentAlignment = Alignment.Center,
        ) {
            Canvas(modifier = Modifier.size(180.dp)) {
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(tertiary.copy(alpha = 0.85f), primary.copy(alpha = 0.35f)),
                        center = Offset(size.width / 2f, size.height / 2f),
                        radius = size.minDimension / 2f,
                    ),
                    radius = size.minDimension / 2f,
                )
            }
            Text("Kairo", style = MaterialTheme.typography.titleMedium)
        }
    }
}
